"""Provides access to PyDSS result data."""
from collections import defaultdict
import copy
import json
import logging
import os
import re

import h5py
import numpy as np
import pandas as pd

from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.element_options import ElementOptions
from PyDSS.exceptions import InvalidParameter
from PyDSS.pydss_project import PyDssProject
from PyDSS.reports import Reports, REPORTS, REPORTS_DIR
from PyDSS.utils.dataframe_utils import read_dataframe, write_dataframe
from PyDSS.utils.utils import dump_data, load_data
from PyDSS.value_storage import ValueStorageBase, DatasetPropertyType, \
    get_dataset_property_type, get_timestamp_path


logger = logging.getLogger(__name__)


class PyDssResults:
    """Interface to perform analysis on PyDSS output data."""
    def __init__(
            self, project_path=None, project=None, in_memory=False,
            frequency=False, mode=False
        ):
        """Constructs PyDssResults object.

        Parameters
        ----------
        project_path : str | None
            Load project from files in path
        project : PyDssProject | None
            Existing project object
        in_memory : bool
            If true, load all exported data into memory.
        frequency : bool
            If true, add frequency column to all dataframes.
        mode : bool
            If true, add mode column to all dataframes.

        """
        options = ElementOptions()
        if project_path is not None:
            self._project = PyDssProject.load_project(project_path)
        elif project is None:
            raise InvalidParameter("project_path or project must be set")
        else:
            self._project = project
        self._fs_intf = self._project.fs_interface
        self._scenarios = []
        filename = self._project.get_hdf_store_filename()
        driver = "core" if in_memory else None
        self._hdf_store = h5py.File(filename, "r", driver=driver)

        if self._project.simulation_config["Exports"]["Log Results"]:
            for name in self._project.list_scenario_names():
                metadata = self._project.read_scenario_export_metadata(name)
                scenario_result = PyDssScenarioResults(
                    name,
                    self.project_path,
                    self._hdf_store,
                    self._fs_intf,
                    metadata,
                    options,
                    frequency=frequency,
                    mode=mode,
                )
                self._scenarios.append(scenario_result)

    def generate_reports(self):
        """Generate all reports specified in the configuration.

        Returns
        -------
        list
            list of report filenames

        """
        return Reports.generate_reports(self)

    def read_report(self, report_name):
        """Return the report data.

        Parameters
        ----------
        report_name : str

        Returns
        -------
        str

        """
        if report_name not in REPORTS:
            raise InvalidParameter(f"invalid report name {report_name}")
        report_cls = REPORTS[report_name]

        # This bypasses self._fs_intf because reports are always extracted.
        reports_dir = os.path.join(self._project.project_path, REPORTS_DIR)
        for filename in os.listdir(reports_dir):
            name, ext = os.path.splitext(filename)
            if name == os.path.splitext(report_cls.FILENAME)[0]:
                path = os.path.join(reports_dir, filename)
                if ext in (".json", ".toml"):
                    return load_data(path)
                if ext in (".csv", ".h5"):
                    return read_dataframe(path)

        raise InvalidParameter(f"did not find report {report_name} in {reports_dir}")

    @property
    def scenarios(self):
        """Return the PyDssScenarioResults instances for the project.

        Returns
        -------
        list
            list of PyDssScenarioResults

        """
        return self._scenarios

    def get_scenario(self, name):
        """Return the PyDssScenarioResults object for scenario with name.

        Parameters
        ----------
        name : str
            Scenario name

        Results
        -------
        PyDssScenarioResults

        Raises
        ------
        InvalidParameter
            Raised if the scenario does not exist.

        """
        for scenario in self._scenarios:
            if name == scenario.name:
                return scenario

        raise InvalidParameter(f"scenario {name} does not exist")

    @property
    def hdf_store(self):
        """Return a handle to the HDF data store.

        Returns
        -------
        h5py.File

        """
        return self._hdf_store

    @property
    def project_path(self):
        """Return the path to the PyDSS project.

        Returns
        -------
        str

        """
        return self._project.project_path

    def read_file(self, path):
        """Read a file from the PyDSS project.

        Parameters
        ----------
        path : str
            Path to the file relative from the project directory.

        Returns
        -------
        str
            Contents of the file

        """
        return self._fs_intf.read_file(path)

    @property
    def simulation_config(self):
        """Return the simulation configuration

        Returns
        -------
        dict

        """
        return self._project.simulation_config


class PyDssScenarioResults:
    """Contains results for one scenario."""
    def __init__(
            self, name, project_path, store, fs_intf, metadata, options,
            frequency=False, mode=False
        ):
        self._name = name
        self._project_path = project_path
        self._hdf_store = store
        self._metadata = metadata
        self._options = options
        self._fs_intf = fs_intf
        self._group = self._hdf_store["Exports"][name]
        self._elem_classes = [
            x for x in self._group.keys() if isinstance(self._group[x], h5py.Group)
        ]
        self._elems_by_class = defaultdict(dict)
        self._props_by_class = defaultdict(list)
        self._elem_props = defaultdict(list)
        self._elem_prop_nums = defaultdict(dict)
        self._indices_df = None
        self._add_frequency = frequency
        self._add_mode = mode
        self._data_format_version = self._hdf_store.attrs["version"]

        if self._data_format_version == "1.0.0":
            self._parse_datasets_v_1_0_0()
        else:
            self._parse_datasets()

    def _parse_datasets(self):
        for elem_class in self._elem_classes:
            class_group = self._group[elem_class]
            self._elems_by_class[elem_class] = list(class_group.keys())
            if not self._elems_by_class[elem_class]:
                continue
            self._props_by_class[elem_class] = set()
            for elem_name in self._elems_by_class[elem_class]:
                for prop in self._group[elem_class][elem_name]:
                    dataset = self._group[elem_class][elem_name][prop]
                    dataset_property_type = get_dataset_property_type(dataset)
                    if dataset_property_type == DatasetPropertyType.NUMBER:
                        self._add_elem_prop_num(elem_class, prop, elem_name, dataset)
                    elif dataset_property_type == DatasetPropertyType.TIMESTAMP:
                        continue
                    else:
                        assert dataset_property_type in (
                            DatasetPropertyType.ELEMENT_PROPERTY,
                            DatasetPropertyType.FILTERED,
                        )
                        self._props_by_class[elem_class].add(prop)
                        self._elem_props[elem_name].append(prop)

    def _parse_datasets_v_1_0_0(self):
        for elem_class in self._elem_classes:
            class_group = self._group[elem_class]
            self._elems_by_class[elem_class] = list(class_group.keys())
            if not self._elems_by_class[elem_class]:
                continue
            # Assume all elements have the same properties stored.
            elem = self._elems_by_class[elem_class][0]
            self._props_by_class[elem_class] = set(class_group[elem].keys())
            for name in self._elems_by_class[elem_class]:
                self._elem_props[name] = list(self._props_by_class[elem_class])

    def _add_elem_prop_num(self, elem_class, prop, elem_name, dataset):
        if prop not in self._elem_prop_nums[elem_class]:
            self._elem_prop_nums[elem_class][prop] = {}
        self._elem_prop_nums[elem_class][prop][elem_name] = dataset[0]

    @property
    def name(self):
        """Return the name of the scenario.

        Returns
        -------
        str

        """
        return self._name

    def export_data(self, path=None, fmt="csv", compress=False):
        """Export data to path.

        Parameters
        ----------
        path : str
            Output directory; defaults to scenario exports path
        fmt : str
            Filer format type (csv, h5)
        compress : bool
            Compress data

        """
        if path is None:
            path = os.path.join(self._project_path, "Exports", self._name)
        os.makedirs(path, exist_ok=True)

        for elem_class in self.list_element_classes():
            for prop in self.list_element_properties(elem_class):
                try:
                    df = self.get_full_dataframe(elem_class, prop)
                except InvalidParameter:
                    logger.info(f"cannot create full dataframe for %s %s", elem_class, prop)
                    self._export_filtered_dataframes(elem_class, prop, path, fmt, compress)
                    continue
                base = "__".join([elem_class, prop])
                filename = os.path.join(path, base + "." + fmt.replace(".", ""))
                write_dataframe(df, filename, compress=compress)

        if self._elem_prop_nums:
            data = copy.deepcopy(self._elem_prop_nums)
            for elem_class, prop, name, val in self.iterate_element_property_numbers():
                # JSON lib cannot serialize complex numbers.
                if isinstance(val, np.ndarray):
                    new_val = []
                    convert_str = val.dtype == "complex"
                    for item in val:
                        if convert_str:
                            item = str(item)
                        new_val.append(item)
                    data[elem_class][prop][name] = new_val
                elif isinstance(val, complex):
                    data[elem_class][prop][name] = str(val)

            filename = os.path.join(path, "element_property_numbers.json")
            dump_data(data, filename, indent=2)

        logger.info("Exported data to %s", path)

    def _export_filtered_dataframes(self, elem_class, prop, path, fmt, compress):
        for name, df in self.iterate_dataframes(elem_class, prop):
            base = "__".join([elem_class, prop, name])
            filename = os.path.join(path, base + "." + fmt.replace(".", ""))
            write_dataframe(df, filename, compress=compress)

    def get_dataframe(self, element_class, prop, element_name, real_only=False, **kwargs):
        """Return the dataframe for an element.

        Parameters
        ----------
        element_class : str
        prop : str
        element_name : str
        real_only : bool
            If dtype of any column is complex, drop the imaginary component.
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        pd.DataFrame

        Raises
        ------
        InvalidParameter
            Raised if the element is not stored.

        """
        if element_name not in self._elem_props:
            raise InvalidParameter(f"element {element_name} is not stored")

        elem_group = self._group[element_class][element_name]
        dataset = elem_group[prop]
        df = DatasetBuffer.to_dataframe(dataset)

        if kwargs:
            options = self._check_options(element_class, prop, **kwargs)
            columns = ValueStorageBase.get_columns(df, element_name, options, **kwargs)
            df = df[columns]

        if self._data_format_version == "1.0.0":
            dataset_property_type = DatasetPropertyType.ELEMENT_PROPERTY
        else:
            dataset_property_type = get_dataset_property_type(dataset)
        if dataset_property_type == DatasetPropertyType.FILTERED:
            timestamp_path = get_timestamp_path(dataset)
            timestamp_dataset = self._hdf_store[timestamp_path]
            df["Timestamp"] = DatasetBuffer.to_datetime(timestamp_dataset)
            df.set_index("Timestamp", inplace=True)
        else:
            self._add_indices_to_dataframe(df)

        if real_only:
            for column in df.columns:
                if df[column].dtype == np.complex:
                    df[column] = [x.real for x in df[column]]

        return df

    @property
    def element_property_numbers(self):
        """Return all element property values stored as numbers.

        Returns
        -------
        dict

        """
        return self._elem_prop_nums

    def get_element_property_number(self, element_class, prop, element_name):
        """Return the number stored for the element property."""
        if element_class not in self._elem_prop_nums:
            raise InvalidParameter(f"{element_class} is not stored")
        if prop not in self._elem_prop_nums[element_class]:
            raise InvalidParameter(f"{prop} is not stored")
        if element_name not in self._elem_prop_nums[element_class][prop]:
            raise InvalidParameter(f"{element_name} is not stored")
        return self._elem_prop_nums[element_class][prop][element_name]

    def get_full_dataframe(self, element_class, prop, real_only=False):
        """Return a dataframe containing all data.  The dataframe is copied.

        Parameters
        ----------
        element_class : str
        prop : str
        real_only : bool
            If dtype of any column is complex, drop the imaginary component.

        Returns
        -------
        pd.DataFrame

        """
        if prop not in self.list_element_properties(element_class):
            raise InvalidParameter(f"property {prop} is not stored")

        master_df = None
        length = None
        for _, df in self.iterate_dataframes(element_class, prop, real_only=real_only):
            cur_len = len(df)
            if master_df is None:
                master_df = df
                length = cur_len
            else:
                if cur_len != length:
                    raise InvalidParameter(
                        "cannot create full dataframe when elements have different indices"
                    )
                for column in ("Frequency", "Simulation Mode"):
                    if column in df.columns:
                        df.drop(column, axis=1, inplace=True)
                master_df = master_df.join(df)

        return master_df

    def get_option_values(self, element_class, prop, element_name):
        """Return the option values for the element property.

        element_class : str
        prop : str
        element_name : str

        Returns
        -------
        list

        """
        df = self.get_dataframe(element_class, prop, element_name)
        return ValueStorageBase.get_option_values(df, element_name)

    def iterate_dataframes(self, element_class, prop, real_only=False, **kwargs):
        """Returns a generator over the dataframes by element name.

        Parameters
        ----------
        element_class : str
        prop : str
        real_only : bool
            If dtype of any column is complex, drop the imaginary component.
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        tuple
            Tuple containing the name or property and a pd.DataFrame

        """
        for name in self.list_element_names(element_class):
            if prop in self._elem_props[name]:
                df = self.get_dataframe(
                    element_class, prop, name, real_only=real_only, **kwargs
                )
                yield name, df

    def iterate_element_property_numbers(self):
        """Return a generator over all element properties stored as numbers.

        Yields
        ------
        tuple
            element_class, property, element_name, value

        """
        for elem_class in self._elem_prop_nums:
            for prop in self._elem_prop_nums[elem_class]:
                for name, val in self._elem_prop_nums[elem_class][prop].items():
                    yield elem_class, prop, name, val

    def list_element_classes(self):
        """Return the element classes stored in the results.

        Returns
        -------
        list

        """
        return self._elem_classes[:]

    def list_element_names(self, element_class, prop=None):
        """Return the element names for a property stored in the results.

        Parameters
        ----------
        element_class : str
        prop : str

        Returns
        -------
        list

        """
        # TODO: prop is deprecated
        return self._elems_by_class.get(element_class, [])

    def list_element_properties(self, element_class, element_name=None):
        """Return the properties stored in the results for a class.

        Parameters
        ----------
        element_class : str
        element_name : str | None
            If not None, list properties only for that name.

        Returns
        -------
        list

        Raises
        ------
        InvalidParameter
            Raised if the element_class is not stored.

        """
        if element_class not in self._props_by_class:
            raise InvalidParameter(f"class={element_class} is not stored")
        if element_name is None:
            return sorted(list(self._props_by_class[element_class]))
        return self._elem_props.get(element_name, [])

    def list_element_property_numbers(self, element_class, element_name):
        nums = []
        for elem_class in self._elem_prop_nums:
            for prop in self._elem_prop_nums[elem_class]:
                for name in self._elem_prop_nums[elem_class][prop]:
                    if name == element_name:
                        nums.append(prop)
        return nums

    def list_element_property_options(self, element_class, prop):
        """List the possible options for the element class and property.

        Parameters
        ----------
        element_class : str
        prop : str

        Returns
        -------
        list

        """
        return self._options.list_options(element_class, prop)

    def list_element_info_files(self):
        """Return the files describing the OpenDSS element objects.

        Returns
        -------
        list
            list of filenames (str)

        """
        return self._metadata["element_info_files"]

    def read_element_info_file(self, filename):
        """Return the contents of file describing an OpenDSS element object.

        Parameters
        ----------
        filename : str
            full path to a file (returned by list_element_info_files) or
            an element class, like "Transformers"

        Returns
        -------
        pd.DataFrame

        """
        if "." not in filename:
            actual = None
            for _file in self.list_element_info_files():
                basename = os.path.splitext(os.path.basename(_file))[0]
                if basename.replace("Info", "") == filename:
                    actual = _file
            if actual is None:
                raise InvalidParameter(
                    f"element info file for {filename} is not stored"
                )
            filename = actual

        return self._fs_intf.read_csv(filename)

    def read_capacitor_changes(self):
        """Read the capacitor state changes from the OpenDSS event log.

        Returns
        -------
        dict
            Maps capacitor names to count of state changes.

        """
        text = self.read_file(self._metadata["event_log"])
        return _read_capacitor_changes(text)

    def read_event_log(self):
        """Returns the event log for the scenario.

        Returns
        -------
        list
            list of dictionaries (one dict for each row in the file)

        """
        text = self.read_file(self._metadata["event_log"])
        return _read_event_log(text)

    def read_pv_profiles(self):
        """Returns exported PV profiles for all PV systems.

        Returns
        -------
        dict

        """
        return self._fs_intf.read_scenario_pv_profiles(self._name)

    def _check_options(self, element_class, prop, **kwargs):
        """Checks that kwargs are valid and returns available option names."""
        for option in kwargs:
            if not self._options.is_option_valid(element_class, prop, option):
                raise InvalidParameter(
                    f"class={element_class} property={prop} option={option} is invalid"
                )

        return self._options.list_options(element_class, prop)

    def read_feeder_head_info(self):
        """Read the feeder head information.

        Returns
        -------
        dict

        """
        return json.loads(self.read_file(f"Exports/{self._name}/FeederHeadInfo.json"))

    def read_file(self, path):
        """Read a file from the PyDSS project.

        Parameters
        ----------
        path : str
            Path to the file relative from the project directory.

        Returns
        -------
        str
            Contents of the file

        """
        return self._fs_intf.read_file(path)

    def _add_indices_to_dataframe(self, df):
        if self._indices_df is None:
            self._make_indices_df()

        df["Timestamp"] = self._indices_df["Timestamp"]
        if self._add_frequency:
            df["Frequency"] = self._indices_df["Frequency"]
        if self._add_mode:
            df["Simulation Mode"] = self._indices_df["Simulation Mode"]
        df.set_index("Timestamp", inplace=True)

    def _make_indices_df(self):
        data = {"Timestamp": self._group["Timestamp"][:]}
        if self._add_frequency:
            data["Frequency"] = self._group["Frequency"][:]
        if self._add_mode:
            data["Simulation Mode"] = self._group["Mode"][:]
        df = pd.DataFrame(data)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="s")
        self._indices_df = df


def _read_capacitor_changes(event_log_text):
    """Read the capacitor state changes from an OpenDSS event log.

    Parameters
    ----------
    event_log_text : str
        Text of event log

    Returns
    -------
    dict
        Maps capacitor names to count of state changes.

    """
    capacitor_changes = {}
    regex = re.compile(r"(Capacitor\.\w+)")

    data = _read_event_log(event_log_text)
    for row in data:
        match = regex.search(row["Element"])
        if match:
            name = match.group(1)
            if name not in capacitor_changes:
                capacitor_changes[name] = 0
            action = row["Action"].replace("*", "")
            if action in ("OPENED", "CLOSED", "STEP UP"):
                capacitor_changes[name] += 1

    return capacitor_changes


def _read_event_log(event_log_text):
    """Return OpenDSS event log information.

    Parameters
    ----------
    event_log_text : str
        Text of event log


    Returns
    -------
    list
        list of dictionaries (one dict for each row in the file)

    """
    data = []
    if not event_log_text:
        return data

    for line in event_log_text.split("\n"):
        if line == "":
            continue
        tokens = [x.strip() for x in line.split(",")]
        row = {}
        for token in tokens:
            name_and_value = [x.strip() for x in token.split("=")]
            name = name_and_value[0]
            value = name_and_value[1]
            row[name] = value
        data.append(row)

    return data

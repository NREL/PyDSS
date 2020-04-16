
import abc
import json
import logging
import os
import pathlib
import shutil

import numpy as np
import pandas as pd

from PyDSS.element_options import ElementOptions
from PyDSS.pyContrReader import pyExportReader
from PyDSS.pyLogger import getLoggerTag
from PyDSS.unitDefinations import unit_info
from PyDSS.exceptions import InvalidParameter
from PyDSS.utils.dataframe_utils import read_dataframe, write_dataframe
from PyDSS.utils.utils import dump_data
from PyDSS.value_storage import get_value_class


class ResultData:
    """Exports data to files."""

    METADATA_FILENAME = "metadata.json"
    INDICES_BASENAME = "indices"

    def __init__(self, options, system_paths, dss_objects,
                 dss_objects_by_class, dss_buses, dss_solver, dss_command,
                 dss_instance):
        if options["Logging"]["Pre-configured logging"]:
            logger_tag = __name__
        else:
            logger_tag = getLoggerTag(options)
        self._logger = logging.getLogger(logger_tag)
        self._dss_solver = dss_solver
        self._results = {}
        self._buses = dss_buses
        self._objects_by_element = dss_objects
        self._objects_by_class = dss_objects_by_class
        self.system_paths = system_paths
        self._elements = []
        self._property_aggregators = []
        self._dss_command = dss_command
        self._dss_instance = dss_instance
        self._start_day = options["Project"]["Start Day"]
        self._end_day = options["Project"]["End Day"]
        self._timestamps = []
        self._frequency = []
        self._simulation_mode = []
        self._hdf_store = None
        self._scenario = options["Project"]["Active Scenario"]
        self._export_format = options["Exports"]["Export Format"]
        self._export_compression = options["Exports"]["Export Compression"]
        self._export_iteration_order = options["Exports"]["Export Iteration Order"]
        self._export_dir = os.path.join(
            self.system_paths["Export"],
            options["Project"]["Active Scenario"],
        )
        # Use / because this is used in HDFStore
        self._export_relative_dir = f"Exports/" + options["Project"]["Active Scenario"]
        self._settings = options
        self._store_frequency = False
        self._store_mode = False
        if options["Project"]["Simulation Type"] == "Dynamic" or \
                options["Frequency"]["Enable frequency sweep"]:
            self._store_frequency = True
            self._store_mode = True

        if options["Exports"]["Export Mode"] == "byElement":
            raise InvalidParameter(
                "Export Mode 'byElement' is not supported by ResultData"
            )
        if options["Helics"]["Co-simulation Mode"]:
            raise InvalidParameter(
                "Co-simulation mode is not supported by ResultData"
            )

        pathlib.Path(self._export_dir).mkdir(parents=True, exist_ok=True)

        self._file_reader = pyExportReader(
            os.path.join(
                system_paths["ExportLists"],
                "ExportMode-byClass.toml",
            ),
        )
        self._export_list = self._file_reader.pyControllers
        self._create_list_by_class()

    @staticmethod
    def updateSubscriptions(self):
        assert False

    def _create_element_list(self, objs, properties):
        elements = []
        element_names = set()
        for property_name in properties:
            assert isinstance(property_name, str)
            for name, obj in objs.items():
                if not obj.Enabled:
                    continue
                if not obj.IsValidAttribute(property_name):
                    raise InvalidParameter(f"{element_class} / {property_name} {name} cannot be exported")
                if name not in element_names:
                    elements.append((name, obj))
                    element_names.add(name)
        return elements



    def _create_list_by_class(self):
        for element_class, properties in self._export_list.items():
            elements = []
            element_names = set()
            if element_class == "Buses":
                objs = self._buses
                elements = self._create_element_list(objs, properties)
            else:
                if element_class in  self._objects_by_class:
                    objs = self._objects_by_class[element_class]
                    elements = self._create_element_list(objs, properties)

            # TODO: refactor prop_aggregators
            prop_aggregators = []
            if self._export_iteration_order == "ValuesByPropertyAcrossElements":
                for prop in properties:
                    prop_aggregators.append(ValuesByPropertyAcrossElements.new(
                        element_class,
                        prop,
                        store_frequency=self._store_frequency,
                        store_mode=self._store_mode,
                    ))

            for name, obj in elements:
                elem = ElementValuesPerProperty.new(
                    element_class,
                    name,
                    properties,
                    obj,
                    store_frequency=self._store_frequency,
                    store_mode=self._store_mode,
                )
                self._elements.append(elem)

                if prop_aggregators:
                    for i, prop in enumerate(properties):
                        prop_aggregators[i].append_element(elem)
            self._property_aggregators += prop_aggregators

    def UpdateResults(self):
        self._timestamps.append(self._dss_solver.GetDateTime())
        self._frequency.append(self._dss_solver.getFrequency())
        self._simulation_mode.append(self._dss_solver.getMode())

        for elem in self._elements:
            elem.add_values()

    def ExportResults(self, hdf_store, fileprefix=""):
        self._hdf_store = hdf_store

        metadata = {
            "type": None,
            "data": [],
            "event_log": None,
            "element_info_files": [],
        }

        if self._settings["Exports"]["Export Event Log"]:
            self._export_event_log(metadata)
        if self._settings["Exports"]["Export Elements"]:
            self._export_elements(metadata)
        if self._elements:
            self._export_indices()
        if self._export_iteration_order == "ElementValuesPerProperty":
            self._export_results_by_element(metadata, fileprefix=fileprefix)
        elif self._export_iteration_order == "ValuesByPropertyAcrossElements":
            self._export_results_by_property(metadata)

        filename = os.path.join(self._export_dir, self.METADATA_FILENAME)
        dump_data(metadata, filename, indent=4)
        self._logger.info("Exported metadata to %s", filename)
        self._hdf_store = None

    def _export_results_by_element(self, metadata, fileprefix=""):
        metadata["type"] = "ElementValuesPerProperty"
        metadata["data"] = {}

        for elem in self._elements:
            if elem.element_class not in metadata["data"]:
                metadata["data"][elem.element_class] = []
            elem_metadata = elem.serialize(
                self._export_dir,
                self._export_format,
                self._export_compression,
            )
            metadata["data"][elem.element_class].append(elem_metadata)

    def _export_results_by_property(self, metadata):
        metadata["type"] = "ValuesByPropertyAcrossElements"

        for prop_agg in self._property_aggregators:
            prop_agg.set_hdf_store(self._hdf_store)
            prop_agg.set_scenario(self._scenario)
            prop_metadata = prop_agg.serialize()
            if prop_metadata is None:
                continue
            metadata["data"].append(prop_metadata)

            if self._settings["Exports"]["Export Tables"]:
                prop_agg.export_data(
                    self._export_dir,
                    self._settings["Exports"]["Export Format"],
                    self._settings["Exports"]["Export Compression"],
                )

    def _export_event_log(self, metadata):
        # TODO: move to a base class
        event_log = "event_log.csv"
        file_path = os.path.join(self._export_dir, event_log)
        if os.path.exists(file_path):
            os.remove(file_path)

        orig = os.getcwd()
        os.chdir(self._export_dir)
        try:
            cmd = "Export EventLog {}".format(event_log)
            out = self._dss_command(cmd)
            if out != event_log:
                raise Exception(f"Failed to export EventLog:  {out}")
            self._logger.info("Exported OpenDSS event log to %s", out)
            metadata["event_log"] = self._export_relative_dir + f"/{event_log}"
        finally:
            os.chdir(orig)

    def _export_dataframe(self, df, basename):
        filename = basename + "." + self._export_format
        write_dataframe(df, filename, compress=self._export_compression)
        self._logger.info("Exported %s", filename)

    def _export_elements(self, metadata):
        dss = self._dss_instance
        exports = (
            # TODO: opendssdirect does not provide a function to export Bus information.
            ("CapacitorsInfo", dss.Capacitors.Count, dss.utils.capacitors_to_dataframe),
            ("FusesInfo", dss.Fuses.Count, dss.utils.fuses_to_dataframe),
            ("GeneratorsInfo", dss.Generators.Count, dss.utils.generators_to_dataframe),
            ("IsourceInfo", dss.Isource.Count, dss.utils.isource_to_dataframe),
            ("LinesInfo", dss.Lines.Count, dss.utils.lines_to_dataframe),
            ("LoadsInfo", dss.Loads.Count, dss.utils.loads_to_dataframe),
            ("MetersInfo", dss.Meters.Count, dss.utils.meters_to_dataframe),
            ("MonitorsInfo", dss.Monitors.Count, dss.utils.monitors_to_dataframe),
            ("PVSystemsInfo", dss.PVsystems.Count, dss.utils.pvsystems_to_dataframe),
            ("ReclosersInfo", dss.Reclosers.Count, dss.utils.reclosers_to_dataframe),
            ("RegControlsInfo", dss.RegControls.Count, dss.utils.regcontrols_to_dataframe),
            ("RelaysInfo", dss.Relays.Count, dss.utils.relays_to_dataframe),
            ("SensorsInfo", dss.Sensors.Count, dss.utils.sensors_to_dataframe),
            ("TransformersInfo", dss.Transformers.Count, dss.utils.transformers_to_dataframe),
            ("VsourcesInfo", dss.Vsources.Count, dss.utils.vsources_to_dataframe),
            ("XYCurvesInfo", dss.XYCurves.Count, dss.utils.xycurves_to_dataframe),
            # TODO This can be very large. Consider making it configurable.
            #("LoadShapeInfo", dss.LoadShape.Count, dss.utils.loadshape_to_dataframe),
        )

        for filename, count_func, get_func in exports:
            if count_func() > 0:
                df = get_func()
                # Always record in CSV format for readability.
                # There are also warning messages from PyTables because the
                # data may contain strings.
                fname = filename + ".csv"
                relpath = os.path.join(self._export_relative_dir, fname)
                filepath = os.path.join(self._export_dir, fname)
                write_dataframe(df, filepath)
                metadata["element_info_files"].append(relpath)
                self._logger.info("Exported %s information to %s.", filename, filepath)

        self._export_transformers(metadata)

    def _export_transformers(self, metadata):
        dss = self._dss_instance
        df_dict = {"Transformer": [], "HighSideConnection": [], "NumPhases": []}

        dss.Circuit.SetActiveClass("Transformer")
        flag = dss.ActiveClass.First()
        while flag > 0:
            name = dss.CktElement.Name()
            df_dict["Transformer"].append(name)
            df_dict["HighSideConnection"].append(dss.Properties.Value("conns").split("[")[1].split(",")[0].strip(" ").lower())
            df_dict["NumPhases"].append(dss.CktElement.NumPhases())
            flag = dss.ActiveClass.Next()

        df = pd.DataFrame.from_dict(df_dict)

        relpath = os.path.join(self._export_relative_dir, "TransformersPhaseInfo.csv")
        filepath = os.path.join(self._export_dir, "TransformersPhaseInfo.csv")
        write_dataframe(df, filepath)
        metadata["element_info_files"].append(relpath)
        self._logger.info("Exported transformer phase information to %s.", filepath)

    def _export_indices(self):
        tuples = list(zip(*[self._timestamps, self._frequency, self._simulation_mode]))
        df = pd.DataFrame(tuples, columns=("timestamp", "frequency", "Simulation mode"))
        path = f"{self._export_relative_dir}/indices"
        self._hdf_store.put(path, df)
        self._logger.debug("Stored indices at %s", path)

    @staticmethod
    def get_indices_filename(path):
        indices_filename = None
        for filename in os.listdir(path):
            basename, ext = os.path.splitext(filename)
            if ext == ".gz":
                basename, ext = os.path.splitext(basename)
            if basename == ResultData.INDICES_BASENAME:
                if indices_filename is not None:
                    raise InvalidParameter(
                        f"found multiple indices files at {path}"
                    )
                indices_filename = filename

        if indices_filename is None:
            raise InvalidParameter(f"did not find indices files at {path}")

        return os.path.join(path, indices_filename)

    @staticmethod
    def get_units(prop, index=None):
        units = unit_info.get(prop)
        if units is None:
            raise InvalidParameter(f"no units are stored for {prop}")

        if isinstance(units, dict):
            if index is None:
                raise InvalidParameter(f"index must be provided for {prop}")
            if index == 0:
                return units["E"]
            elif index == 1:
                return units["O"]
            else:
                raise InvalidParameter("index must be 0 or 1")

        return units


class ElementData(abc.ABC):
    DELIMITER = "__"

    def __init__(self, element_class,
                 store_frequency=False, store_mode=False, scenario=None,
                 hdf_store=None):
        self.cache_data = bool(int(os.environ.get("PYDSS_CACHE_DATA", 0)))
        self._cached_df = None
        self._element_class = element_class
        self._indices_df = None
        self._value_class = None
        self._store_frequency = store_frequency
        self._store_mode = store_mode
        self._scenario = scenario
        self._hdf_store = hdf_store

    @abc.abstractmethod
    def serialize(self, path, fmt, compress):
        """Serialize metadata into a dictionary and write data to media."""

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, data):
        """Deserialize from a dictionary."""

    @abc.abstractmethod
    def export_data(self, path, fmt, compress):
        """Export data to path.

        Parameters
        ----------
        path : str
            Output directory
        fmt : str
            Filer format type (csv, h5)
        compress : bool
            Compress data

        """

    @property
    def path(self):
        return self._path

    def get_full_dataframe(self):
        """Return a dataframe containing all data.  The dataframe is copied.

        Returns
        -------
        pd.DataFrame

        """
        df = self._get_dataframe().copy(deep=True)
        self._add_indices_to_dataframe(df)
        return df

    def _get_dataframe(self):
        def get_df():
            path = f"Exports/{self._scenario}/{self._get_df_id()}"
            return self._hdf_store.get(path)

        if self.cache_data:
            if self._cached_df is not None:
                df = self._cached_df
            else:
                df = get_df()
                self._cached_df = df
        else:
            df = get_df()

        return df

    def _add_indices_to_dataframe(self, df):
        if self._indices_df is None:
            self._indices_df = self._hdf_store.get(f"Exports/{self._scenario}/indices")

        df["timestamp"] = self._indices_df["timestamp"]
        if self._store_frequency:
            df["frequency"] = self._indices_df["frequency"]
        if self._store_mode:
            df["Simulation mode"] = self._indices_df["Simulation mode"]
        df.set_index(("timestamp"), inplace=True)

    @abc.abstractmethod
    def iterate_dataframes(self, options, **kwargs):
        """Return a generator of stored dataframes."""

    def set_value_class(self, value_class):
        self._value_class = value_class


class ElementValuesPerProperty(ElementData):
    """Contains values for one element for all properties of an element class."""
    def __init__(self, element_class, name, properties, obj, data,
                 store_frequency=False, store_mode=False,
                 scenario=None, hdf_store=None):
        super(ElementValuesPerProperty, self).__init__(
            element_class, store_frequency, store_mode,
            scenario=scenario, hdf_store=hdf_store)
        self._properties = properties
        self._name = name
        self._obj = obj
        self._data = data
        self._indices_df = None

    @classmethod
    def new(cls, element_class, name, properties, obj, store_frequency=False,
            store_mode=False):
        """Creates a new instance of ElementValuesPerProperty."""
        data = {x: None for x in properties}
        return cls(element_class, name, properties, obj, data,
                   store_frequency=store_frequency, store_mode=store_mode)

    def serialize(self, path, fmt, compress):
        # FIXME
        assert False, "Serializing this type is broken because it produces duplicate column names"
        data = {}
        for field in ("element_class", "name", "properties"):
            data[field] = getattr(self, field)

        dataframes = []
        for prop in self.properties:
            _data = self.get_data(prop)
            if not _data:
                continue
            df = _data.to_dataframe()
            # TODO: this might be broken but this code path is not expected
            # to be used much.
            #columns = self._value_class.get_columns(df, self._name, options)
            #df.columns = columns
            dataframes.append(df)

        df = pd.concat(dataframes, axis=1, copy=False)
        filename = self._make_filename() + "." + fmt
        fullpath = os.path.join(path, filename)
        write_dataframe(df, fullpath, compress=compress)
        data["file"] = fullpath
        data["value_class"] = self._value_class.__name__

        return data

    @classmethod
    def deserialize(cls, data):
        data_filename = data["file"]
        path = os.path.dirname(data_filename)
        obj = cls(
            data["element_class"],
            data["name"],
            data["properties"],
            None,
            None,
            path,
            data_filename,
        )
        value_class = get_value_class(data["value_class"])
        obj.set_value_class(value_class)
        return obj

    def add_values(self):
        for prop in self.properties:
            value = self._obj.GetValue(prop, convert=True)
            if self._data[prop] is None:
                self._data[prop] = value
            else:
                self._data[prop].append(value)
            if self._value_class is None:
                self.set_value_class(type(value))

    @property
    def element_class(self):
        return self._element_class

    @property
    def name(self):
        return self._name

    @property
    def properties(self):
        return self._properties[:]

    @property
    def value_class(self):
        return self._value_class

    def get_data(self, prop):
        assert self._data is not None
        return self._data[prop]

    def get_dataframe(self, prop, options, **kwargs):
        """Return a dataframe for a property.

        Parameters
        ----------
        prop : str
            property of an ElementValuesPerProperty Class
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        pd.DataFrame

        """
        df = self._get_dataframe()
        columns = self._value_class.get_columns(df, self._name, options, **kwargs)
        df = df[columns]
        self._add_indices_to_dataframe(df)
        return df

    def iterate_dataframes(self, prop, options, **kwargs):
        """Returns a generator over the dataframes by property.

        Returns
        -------
        tuple
            (str, pd.DataFrame)

        """
        df_master = self._get_dataframe()
        columns = self._value_class.get_columns(df_master, self._name, options, **kwargs)
        df = df_master[columns]
        self._add_indices_to_dataframe(df)
        return prop, df

    @staticmethod
    def get_fields_from_filename(filename):
        basename = os.path.splitext(os.path.basename(filename))[0]
        return basename.split(ElementValuesPerProperty.DELIMITER)

    def _get_df_id(self):
        return self.DELIMITER.join((self.element_class, self.name))

    def _make_column_name(self, prop, index):
        return self.DELIMITER.join((self.name, prop, str(index)))

    def export_data(self, path, fmt, compress):
        assert False


class ValuesByPropertyAcrossElements(ElementData):
    """Contains values for all elements for a specific property."""
    def __init__(self, element_class, prop, elements, element_names,
                 store_frequency=False, store_mode=False,
                 scenario=None, hdf_store=None):
        super(ValuesByPropertyAcrossElements, self).__init__(
            element_class,
            store_frequency=store_frequency,
            store_mode=store_mode,
            scenario=scenario,
            hdf_store=hdf_store,
        )
        self._property = prop
        self._elements = elements
        self._element_names = element_names
        self._value_class = None

    @classmethod
    def new(cls, element_class, prop, store_frequency=False, store_mode=False):
        elements = []
        element_names = []
        return cls(element_class, prop, elements, element_names,
                   store_frequency=store_frequency, store_mode=store_mode)

    def export_data(self, path, fmt, compress):
        all_options = ElementOptions()
        options = all_options.list_options(self.element_class, self.prop)
        for name, df in self.iterate_dataframes(options):
            base = "__".join([self.element_class, self.prop, name])
            filename = os.path.join(path, base + "." + fmt.replace(".", ""))
            write_dataframe(df, filename, compress=compress)

    def set_hdf_store(self, hdf_store):
        """Set the HDFStore for the object."""
        self._hdf_store = hdf_store

    def set_scenario(self, scenario):
        """Set the scenario for the object."""
        self._scenario = scenario

    def serialize(self):
        data = {
            "element_class": self.element_class,
            "property": self.prop,
            "scenario": self._scenario,
        }

        if self._elements:
            self.set_value_class(self._elements[0].value_class)

        dataframes = []
        for elem in self._elements:
            _data = elem.get_data(self._property)
            if not _data:
                continue
            #if not isinstance(_data, list):
            df = _data.to_dataframe()
            dataframes.append(df)

        if len(dataframes):
            df = pd.concat(dataframes, axis=1, copy=False)
            df_id = self._get_df_id()
            path = f"Exports/{self._scenario}/{df_id}"
            self._hdf_store.put(path, df)

            data["df_id"] = df_id
            data["element_names"] = self._element_names
            data["value_class"] = self._value_class.__name__
            return data
        else:
            print(f'NO DF: {self._element_class} - {self._property} - {self._element_names}')
            # TODO: self._value_class can be None, so this fails.
            #print('NO DF: {} - {}'.format(self._value_class.__name__, self._element_names))
            return None

    @classmethod
    def deserialize(cls, hdf_store, data):
        obj = cls(
            data["element_class"],
            data["property"],
            [],  # TODO
            data["element_names"],
            scenario=data["scenario"],
            hdf_store=hdf_store,
        )

        obj.set_value_class(get_value_class(data["value_class"]))
        return obj

    def _make_column_name(self, name, index):
        return self.DELIMITER.join((name, str(index)))

    def _get_df_id(self):
        return self.DELIMITER.join((self._element_class, self._property))

    def append_element(self, element):
        self._elements.append(element)
        self._element_names.append(element.name)

    @property
    def element_class(self):
        return self._element_class

    @property
    def element_names(self):
        return self._element_names

    @property
    def prop(self):
        return self._property

    def get_dataframe(self, element_name, options, **kwargs):
        """Return a dataframe for a property.

        Parameters
        ----------
        element_name : str
        options : list
            list of str
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        pd.DataFrame

        """
        assert self._value_class is not None
        df = self._get_dataframe()
        columns = self._value_class.get_columns(df, element_name, options, **kwargs)
        df = df[columns]
        self._add_indices_to_dataframe(df)
        return df

    def get_option_values(self, element_name):
        """Return option values in the data.

        Parameters
        ----------
        element_name : str

        Returns
        -------
        list

        """
        assert self._value_class is not None
        df = self._get_dataframe()
        return self._value_class.get_option_values(df, element_name)

    def iterate_dataframes(self, options, **kwargs):
        """Returns a generator over the dataframes by element name.

        Returns
        -------
        tuple
            (str, pd.DataFrame)

        """
        df_master = self._get_dataframe()
        for name in self._element_names:
            columns = self._value_class.get_columns(df_master, name, options, **kwargs)
            df = df_master[columns]
            self._add_indices_to_dataframe(df)
            yield name, df

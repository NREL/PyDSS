
import abc
import logging
import os
import pathlib
import re
import shutil

import pandas as pd

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
                 dss_objects_by_class, dss_buses, dss_solver, dss_command):
        if options["Pre-configured logging"]:
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
        self._settings = options
        self._start_day = options["Start Day"]
        self._end_day = options["End Day"]
        self._timestamps = []
        self._frequency = []
        self._simulation_mode = []
        self._export_format = options["Export Format"]
        self._export_compression = options["Export Compression"]
        self._export_iteration_order = options["Export Iteration Order"]
        self._export_dir = os.path.join(
            self.system_paths["Export"],
            options["Active Scenario"],
        )
        self._event_log = None

        if self._settings["Export Mode"] == "byElement":
            raise InvalidParameter(
                "Export Mode 'byElement' is not supported by ResultData"
            )
        if self._settings["Co-simulation Mode"]:
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
                if not obj.IsValidAttribute(property_name):
                    raise InvalidParameter(f"{element_class} / {property_name} {name} cannot be exported")
                #TODO: Will commenting this be an issue ever Dan?
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
                    prop_aggregators.append(ValuesByPropertyAcrossElements.new(element_class, prop))

            for name, obj in elements:
                elem = ElementValuesPerProperty.new(element_class, name, properties, obj)
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

    def ExportResults(self, fileprefix=""):
        self._export_indices()
        #self._export_event_log()
        if self._export_iteration_order == "ElementValuesPerProperty":
            self._export_results_by_element(fileprefix=fileprefix)
        elif self._export_iteration_order == "ValuesByPropertyAcrossElements":
            self._export_results_by_property(fileprefix=fileprefix)

    def _export_common(self, metadata):
        metadata["event_log"] = self._event_log
        metadata["element_info_files"] = []

        if self._settings["Export Elements"]:
            regex = re.compile(r"^\w+Info\.{}".format(self._export_format))
            for filename in os.listdir(self._export_dir):
                if regex.search(filename):
                    metadata["element_info_files"].append(os.path.join(
                        self._export_dir, filename
                    ))

    def _export_results_by_element(self, fileprefix=""):
        metadata = {"data": {}, "type": "ElementValuesPerProperty"}
        self._export_common(metadata)

        for elem in self._elements:
            if elem.element_class not in metadata["data"]:
                metadata["data"][elem.element_class] = []
            elem_metadata = elem.serialize(
                self._export_dir,
                self._export_format,
                self._export_compression,
            )
            metadata["data"][elem.element_class].append(elem_metadata)

        filename = os.path.join(self._export_dir, self.METADATA_FILENAME)
        dump_data(metadata, filename, indent=4)
        self._logger.info("Exported metadata to %s", filename)

    def _export_results_by_property(self, fileprefix=""):
        metadata = {"data": [], "type": "ValuesByPropertyAcrossElements"}
        self._export_common(metadata)

        for prop_agg in self._property_aggregators:
            prop_metadata = prop_agg.serialize(
                self._export_dir,
                self._export_format,
                self._export_compression,
            )
            metadata["data"].append(prop_metadata)

        filename = os.path.join(self._export_dir, self.METADATA_FILENAME)
        dump_data(metadata, filename, indent=4)
        self._logger.info("Exported metadata to %s", filename)

    def _export_event_log(self):
        # TODO: move to a base class
        event_log = "event_log.csv"
        cmd = "Export EventLog {}".format(event_log)
        out = self._dss_command(cmd)
        self._logger.info("Exported OpenDSS event log to %s", out)
        file_path = os.path.join(self._export_dir, event_log)
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(event_log, self._export_dir)
        self._event_log = os.path.join(self._export_dir, event_log)

    def _export_dataframe(self, df, basename):
        filename = basename + "." + self._export_format
        write_dataframe(df, filename, compress=self._export_compression)
        self._logger.info("Exported %s", filename)

    def _export_indices(self):
        tuples = list(zip(*[self._timestamps, self._frequency, self._simulation_mode]))
        df = pd.DataFrame(tuples, columns=("timestamp", "frequency", "Simulation mode"))
        path = os.path.join(self._export_dir, ResultData.INDICES_BASENAME + "." + self._export_format)
        write_dataframe(df, path, compress=self._export_compression)

    @staticmethod
    def get_indices_filename(path):
        indices_filename = None
        for filename in os.listdir(path):
            if os.path.splitext(filename)[0] == ResultData.INDICES_BASENAME:
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

    def __init__(self, element_class, path, data_filename):
        self.cache_data = bool(int(os.environ.get("PYDSS_CACHE_DATA", 0)))
        self._cached_df = None
        self._element_class = element_class
        self._data_filename = data_filename
        self._path = path
        self._indices_df = None
        self._value_class = None

    @abc.abstractmethod
    def serialize(self, path, fmt, compress):
        """Serialize metadata into a dictionary and write data to media."""

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, data):
        """Deserialize from a dictionary."""

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
        if self.cache_data:
            if self._cached_df is not None:
                df = self._cached_df
            else:
                df = read_dataframe(self._data_filename)
                self._cached_df = df
        else:
            df = read_dataframe(self._data_filename)

        return df

    def _add_indices_to_dataframe(self, df):
        if self._indices_df is None:
            self._indices_df = read_dataframe(
                ResultData.get_indices_filename(self.path)
            )

        df["timestamp"] = self._indices_df["timestamp"]
        df["frequency"] = self._indices_df["frequency"]
        df["Simulation mode"] = self._indices_df["Simulation mode"]
        df.set_index(("timestamp"), inplace=True)

    @abc.abstractmethod
    def iterate_dataframes(self, label=None):
        """Return a generator of stored dataframes."""

    def set_value_class(self, value_class):
        self._value_class = value_class


class ElementValuesPerProperty(ElementData):
    """Contains values for one element for all properties of an element class."""
    def __init__(self, element_class, name, properties, obj, data, path, data_filename):
        super(ElementValuesPerProperty, self).__init__(element_class, path, data_filename)
        self._properties = properties
        self._name = name
        self._obj = obj
        self._data = data
        self._indices_df = None

    @classmethod
    def new(cls, element_class, name, properties, obj):
        """Creates a new instance of ElementValuesPerProperty."""
        data = {x: None for x in properties}
        return cls(element_class, name, properties, obj, data, None, None)

    def serialize(self, path, fmt, compress):
        data = {}
        for field in ("element_class", "name", "properties"):
            data[field] = getattr(self, field)

        dataframes = []
        for prop in self.properties:
            _data = self.get_data(prop)
            if not _data:
                continue
            df = _data.to_dataframe()
            columns = self._value_class.get_columns(df, self._name, prop)
            df.columns = columns
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
        for  prop in self.properties:
            value = self._obj.GetValue(prop, convert=True)
            if isinstance(value, list):
                for v in value:
                    if self._data[prop] is None:
                        self._data[prop] = v
                    else:
                        self._data[prop].append(v)
                    if self._value_class is None:
                        self.set_value_class(type(v))
            else:
                # TODO: please check to this if this is correct
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

    def get_dataframe(self, prop, label=None):
        """Return a dataframe for a property.

        Parameters
        ----------
        prop : str
            property of an ElementValuesPerProperty Class
        index : int
            For compound values return only this value. If None, return all.
            For example, to get only Current Magnitudes from a property called
            'CurrentsMagAng', set index=0.

        Returns
        -------
        pd.DataFrame

        """
        df = self._get_dataframe()
        columns = self._value_class.get_columns(df, self._name, prop, label=label)
        df = df[columns]
        self._add_indices_to_dataframe(df)
        return df

    def iterate_dataframes(self, label=None):
        """Returns a generator over the dataframes by property.

        Returns
        -------
        tuple
            (str, pd.DataFrame)

        """
        df_master = self._get_dataframe()
        for prop in self._properties:
            columns = self._value_class.get_columns(df_master, self._name, prop)
            df = df_master[columns]
            self._add_indices_to_dataframe(df)
            yield prop, df

    @staticmethod
    def get_fields_from_filename(filename):
        basename = os.path.splitext(os.path.basename(filename))[0]
        return basename.split(ElementValuesPerProperty.DELIMITER)

    def _make_filename(self):
        return self.DELIMITER.join((self.element_class, self.name))

    def _make_column_name(self, prop, index):
        return self.DELIMITER.join((self.name, prop, str(index)))


class ValuesByPropertyAcrossElements(ElementData):
    """Contains values for all elements for a specific property."""
    def __init__(self, element_class, prop, elements, element_names, path, data_filename):
        super(ValuesByPropertyAcrossElements, self).__init__(element_class, path, data_filename)
        self._property = prop
        self._elements = elements
        self._element_names = element_names
        self._value_class = None

    @classmethod
    def new(cls, element_class, prop):
        elements = []
        element_names = []
        return cls(element_class, prop, elements, element_names, None, None)

    def serialize(self, path, fmt, compress):
        data = {
            "element_class": self.element_class,
            "property": self.prop,
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
            filename = self._make_filename() + "." + fmt
            fullpath = os.path.join(path, filename)
            write_dataframe(df, fullpath, compress=compress)

            data["file"] = fullpath
            data["element_names"] = self._element_names
            data["value_class"] = self._value_class.__name__
            return data
        else:
            print('NO DF: {} - {}'.format(self._value_class.__name__, self._element_names))

    @classmethod
    def deserialize(cls, data):
        data_filename = data["file"]
        obj = cls(
            data["element_class"],
            data["property"],
            [],  # TODO
            data["element_names"],
            os.path.dirname(data_filename),
            data_filename,
        )

        obj.set_value_class(get_value_class(data["value_class"]))
        return obj

    def _make_column_name(self, name, index):
        return self.DELIMITER.join((name, str(index)))

    def _make_filename(self):
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

    def get_dataframe(self, element_name, label=None):
        """Return a dataframe for a property.

        Parameters
        ----------
        element_name : str
        index : int
            For compound values return only this value. If None, return all.
            For example, to get only Current Magnitudes from a property called
            'CurrentsMagAng', set index=0.

        Returns
        -------
        pd.DataFrame

        """
        assert self._value_class is not None
        df = self._get_dataframe()
        columns = self._value_class.get_columns(df, element_name, self._property, label=label)
        df = df[columns]
        self._add_indices_to_dataframe(df)
        return df

    def iterate_dataframes(self, label=None):
        """Returns a generator over the dataframes by element name.

        Returns
        -------
        tuple
            (str, pd.DataFrame)

        """
        df_master = self._get_dataframe()
        for name in self._element_names:
            columns = self._value_class.get_columns(df_master, name, self._property, label=label)
            df = df_master[columns]
            self._add_indices_to_dataframe(df)
            yield name, df

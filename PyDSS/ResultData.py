
import abc
import json
import logging
import os
import pathlib
import shutil

import numpy as np
import pandas as pd

from PyDSS.pyContrReader import pyExportReader
from PyDSS.pyLogger import getLoggerTag
from PyDSS.unitDefinations import unit_info
from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.exceptions import InvalidParameter
from PyDSS.utils.dataframe_utils import read_dataframe, write_dataframe
from PyDSS.utils.utils import dump_data
from PyDSS.value_storage import ValueContainer


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
        self._dss_command = dss_command
        self._dss_instance = dss_instance
        self._start_day = options["Project"]["Start Day"]
        self._end_day = options["Project"]["End Day"]
        self._time_dataset = None
        self._frequency_dataset = None
        self._mode_dataset = None
        self._simulation_mode = []
        self._hdf_store = None
        self._scenario = options["Project"]["Active Scenario"]
        self._export_format = options["Exports"]["Export Format"]
        self._export_compression = options["Exports"]["Export Compression"]
        self._export_iteration_order = options["Exports"]["Export Iteration Order"]
        self._max_chunk_bytes = options["Exports"]["HDF Max Chunk Bytes"]
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

            for name, obj in elements:
                elem = ElementData.new(
                    element_class,
                    name,
                    properties,
                    obj,
                    max_chunk_bytes=self._max_chunk_bytes,
                    store_frequency=self._store_frequency,
                    store_mode=self._store_mode,
                )
                self._elements.append(elem)

    def InitializeDataStore(self, hdf_store, num_steps):
        self._hdf_store = hdf_store
        self._time_dataset = DatasetBuffer(
            hdf_store=hdf_store,
            path=f"Exports/{self._scenario}/Timestamp",
            max_size=num_steps,
            dtype=float,
            columns=("Timestamp",),
            max_chunk_bytes=self._max_chunk_bytes
        )
        self._frequency_dataset = DatasetBuffer(
            hdf_store=hdf_store,
            path=f"Exports/{self._scenario}/Frequency",
            max_size=num_steps,
            dtype=float,
            columns=("Frequency",),
            max_chunk_bytes=self._max_chunk_bytes
        )
        self._mode_dataset = DatasetBuffer(
            hdf_store=hdf_store,
            path=f"Exports/{self._scenario}/Mode",
            max_size=num_steps,
            dtype="S10",
            columns=("Mode",),
            max_chunk_bytes=self._max_chunk_bytes
        )

        for element in self._elements:
            element.initialize_data_store(hdf_store, self._scenario, num_steps)

    def UpdateResults(self):
        self.CurrentResults = {}
        self._time_dataset.write_value(self._dss_solver.GetDateTime().timestamp())
        self._frequency_dataset.write_value(self._dss_solver.getFrequency())
        self._mode_dataset.write_value(self._dss_solver.getMode())

        for elem in self._elements:
            data = elem.append_values()
            self.CurrentResults = {**self.CurrentResults, **data}
        return self.CurrentResults

    def ExportResults(self, fileprefix=""):
        self.FlushData()
        metadata = {
            "event_log": None,
            "element_info_files": [],
        }

        if self._settings["Exports"]["Export Event Log"]:
            self._export_event_log(metadata)
        if self._settings["Exports"]["Export Elements"]:
            self._export_elements(metadata)

        filename = os.path.join(self._export_dir, self.METADATA_FILENAME)
        dump_data(metadata, filename, indent=4)
        self._logger.info("Exported metadata to %s", filename)
        self._hdf_store = None

    def FlushData(self):
        for dataset in (self._time_dataset, self._frequency_dataset, self._mode_dataset):
            dataset.flush_data()
        for element in self._elements:
            element.flush_data()

    def _export_results_by_element(self, metadata, fileprefix=""):
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

    def max_num_bytes(self):
        """Return the maximum number of bytes the container could hold.

        Returns
        -------
        int

        """
        total = 0
        for element in self._elements:
            total += element.max_num_bytes()
        return total


class ElementData:
    DELIMITER = "__"

    def __init__(self, element_class, name, properties, obj, data, max_chunk_bytes,
                 store_frequency=False, store_mode=False,
                 scenario=None, hdf_store=None):
        self._properties = properties
        self._name = name
        self._obj = obj
        self._data = data
        self._num_steps = None
        self._element_class = element_class
        self._scenario = scenario
        self._hdf_store = hdf_store
        self._max_chunk_bytes = max_chunk_bytes

    @classmethod
    def new(cls, element_class, name, properties, obj, max_chunk_bytes,
            store_frequency=False, store_mode=False):
        """Creates a new instance of ElementData."""
        data = {x: None for x in properties}
        return cls(element_class, name, properties, obj, data, max_chunk_bytes,
                   store_frequency=store_frequency, store_mode=store_mode)

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
        pass

    @property
    def path(self):
        return self._path

    def initialize_data_store(self, hdf_store, scenario, num_steps):
        self._hdf_store = hdf_store
        self._num_steps = num_steps
        self._scenario = scenario

    def append_values(self):
        curr_data = {}
        for prop in self.properties:
            value = self._obj.GetValue(prop, convert=True)
            if len(value.make_columns()) > 1:
                for property, val in zip(value.make_columns(), value._value):
                    curr_data[property] = val
            else:
                curr_data[value.make_columns()[0]] = value._value
            if self._data[prop] is None:
                path = f"Exports/{self._scenario}/{self._element_class}/{self._name}/{prop}"
                self._data[prop] = ValueContainer(
                    value,
                    self._hdf_store,
                    path,
                    self._num_steps,
                    max_chunk_bytes=self._max_chunk_bytes,
                )
            self._data[prop].append(value)
        return curr_data

    @property
    def element_class(self):
        return self._element_class

    def flush_data(self):
        """Flush any outstanding data to disk."""
        for container in self._data.values():
            assert container is not None, \
                "flush cannot be called until at least one value has been collected"
            container.flush_data()

    def max_num_bytes(self):
        """Return the maximum number of bytes the element could store.

        Returns
        -------
        int

        """
        total = 0
        for container in self._data.values():
            assert container is not None, \
                "max_num_bytes cannot be called until at least one value has been collected"
            total += container.max_num_bytes()
        return total

    @property
    def name(self):
        return self._name

    @property
    def properties(self):
        return self._properties[:]

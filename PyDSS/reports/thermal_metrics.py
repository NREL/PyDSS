
from datetime import timedelta
import logging
import os

from PyDSS.common import StoreValuesType
from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.reports.reports import ReportBase
from PyDSS.utils.utils import dump_data


logger = logging.getLogger(__name__)


class ThermalMetrics(ReportBase):
    """Reports thermal metrics."""

    DEFAULTS = {
        "line_window_size_hours": 1,
        "line_loading_percent_threshold": 120,
        "line_loading_percent_moving_average_threshold": 100,
        "transformer_loading_percent_threshold": 150,
        "transformer_window_size_hours": 2,
        "transformer_loading_percent_moving_average_threshold": 120,
    }
    FILENAME = "thermal_metrics.json"
    NAME = "Thermal Metrics"

    def __init__(self, name, results, simulation_config):
        super().__init__(name, results, simulation_config)
        self._options = self._report_options
        self._num_lines = 0
        self._num_transformers = 0
        self._resolution = self._get_simulation_resolution()
        inputs = self.get_inputs_from_defaults(self._simulation_config, self.NAME)
        self._store_type = self._get_store_type(inputs, self._resolution)
        self._line_window_size, self._transformer_window_size = self._get_window_sizes(inputs, self._resolution)

        prop_name = "ExportOverloadsMetric"
        if self._store_type == StoreValuesType.MOVING_AVERAGE:
            prop_name += "AvgMax"
            node_names1 = self._scenarios[0].list_element_value_names("CktElement", prop_name)
            node_names2 = self._scenarios[1].list_element_value_names("CktElement", prop_name)
        else:
            node_names1 = self._scenarios[0].list_element_names("CktElement", prop_name)
            node_names2 = self._scenarios[1].list_element_names("CktElement", prop_name)
        assert len(node_names1) == len(node_names2)
        self._node_names = node_names1

        for name in self._node_names:
            if name.startswith("Line"):
                self._num_lines += 1
            elif name.startswith("Transformer"):
                self._num_transformers += 1
            else:
                continue

    def generate(self, output_dir):
        data = {
            "num_lines": self._num_lines,
            "num_transformers": self._num_transformers,
            "max_violations": self._get_max_violations(),
            "moving_average_max_violations": self._get_moving_average_max_violations(),
        }

        self._export_json_report(data, output_dir, "thermal_metrics.json")

    def _get_max_violations(self):
        if self._store_type == StoreValuesType.ALL:
            data = self._get_max_violations_instantaneous()
        elif self._store_type == StoreValuesType.MOVING_AVERAGE:
            data = self._get_max_violations_moving_average()
        return data

    def _get_max_violations_moving_average(self):
        data = {}
        for scenario in self._results.scenarios:
            data[scenario.name] = {"Lines": [], "Transformers": []}
            data[scenario.name] = {"Lines": [], "Transformers": []}
            for name in scenario.list_element_value_names("CktElement", "ExportOverloadsMetricMax"):
                num = scenario.get_element_property_value("CktElement", "ExportOverloadsMetricMax", name)
                if name.startswith("Line"):
                    items = data[scenario.name]["Lines"]
                    threshold = self._options["line_loading_percent_threshold"]
                elif name.startswith("Transformer"):
                    items = data[scenario.name]["Transformers"]
                    threshold = self._options["transformer_loading_percent_threshold"]
                else:
                    continue
                if num > threshold:
                    items.append(
                        {
                            "name": name,
                            "max_violation": num,
                        }
                    )

        return data

    def _get_max_violations_instantaneous(self):
        data = {}
        for scenario in self._results.scenarios:
            data[scenario.name] = {"Lines": [], "Transformers": []}
            dfs = scenario.get_filtered_dataframes("CktElement", "ExportOverloadsMetric")
            for name, df in dfs.items():
                if name.startswith("Line"):
                    items = data[scenario.name]["Lines"]
                    threshold = self._options["line_loading_percent_threshold"]
                elif name.startswith("Transformers"):
                    items = data[scenario.name]["Transformers"]
                    threshold = self._options["transformer_loading_percent_threshold"]
                else:
                    continue
                max_val = df.iloc[:, 0].max()
                if max_val > threshold:
                    items.append({"name": name, "max_violation": max_val})

        return data

    def _get_moving_average_max_violations(self):
        if self._store_type == StoreValuesType.ALL:
            data = self._get_moving_average_max_violations_instantaneous()
        elif self._store_type == StoreValuesType.MOVING_AVERAGE:
            data = self._get_moving_average_max_violations_moving_average()
        return data

    def _get_moving_average_max_violations_moving_average(self):
        data = {}
        for scenario in self._results.scenarios:
            data[scenario.name] = {"Lines": [], "Transformers": []}
            data[scenario.name] = {"Lines": [], "Transformers": []}
            for name in scenario.list_element_value_names("CktElement", "ExportOverloadsMetricAvgMax"):
                num = scenario.get_element_property_value("CktElement", "ExportOverloadsMetricAvgMax", name)
                if name.startswith("Line"):
                    items = data[scenario.name]["Lines"]
                    threshold = self._options["line_loading_percent_moving_average_threshold"]
                elif name.startswith("Transformer"):
                    items = data[scenario.name]["Transformers"]
                    threshold = self._options["transformer_loading_percent_moving_average_threshold"]
                else:
                    continue
                if num > threshold:
                    items.append(
                        {
                            "name": name,
                            "moving_average_max_violation": num,
                        }
                    )

        return data

    def _get_moving_average_max_violations_instantaneous(self):
        data = {}
        for scenario in self._results.scenarios:
            data[scenario.name] = {"Lines": [], "Transformers": []}
            data[scenario.name] = {"Lines": [], "Transformers": []}
            dfs = scenario.get_filtered_dataframes("CktElement", "ExportOverloadsMetric")
            for name, df in dfs.items():
                if name.startswith("Line"):
                    items = data[scenario.name]["Lines"]
                    threshold = self._options["line_loading_percent_moving_average_threshold"]
                    window_size = self._line_window_size
                elif name.startswith("Transformers"):
                    items = data[scenario.name]["Transformers"]
                    threshold = self._options["transformer_loading_percent_moving_average_threshold"]
                    window_size = self._transformer_window_size
                else:
                    continue
                window_size = int(window_size / self._resolution)
                moving_avg_max = df.rolling(window_size).mean().max()[0]
                if moving_avg_max > threshold:
                    items.append(
                        {
                            "name": name,
                            "moving_average_max_violation": moving_avg_max,
                        }
                    )
        return data

    @staticmethod
    def _get_store_type(inputs, resolution):
        if inputs.get("force_instantaneous", False):
            val = StoreValuesType.ALL
        elif inputs.get("force_moving_average", False):
            val = StoreValuesType.MOVING_AVERAGE
        elif resolution >= timedelta(minutes=15):
            val = StoreValuesType.ALL
        else:
            val = StoreValuesType.MOVING_AVERAGE

        return val

    @staticmethod
    def get_required_exports(simulation_config):
        resolution = timedelta(seconds=simulation_config["Project"]["Step resolution (sec)"])
        inputs = ThermalMetrics.get_inputs_from_defaults(simulation_config, ThermalMetrics.NAME)
        store_type = ThermalMetrics._get_store_type(inputs, resolution)
        inputs = ThermalMetrics.get_inputs_from_defaults(simulation_config, ThermalMetrics.NAME)
        if store_type == StoreValuesType.ALL:
            data = ThermalMetrics._get_required_exports_instantaneous(inputs)
        elif store_type == StoreValuesType.MOVING_AVERAGE:
            data = ThermalMetrics._get_required_exports_moving_average(inputs, resolution)
        else:
            assert False

        return data

    @staticmethod
    def _get_required_exports_instantaneous(inputs):
        limits_max = min(
            inputs["line_loading_percent_threshold"],
            inputs["transformer_loading_percent_threshold"],
        )
        return {
            "CktElement": [
                {
                    "property": "ExportOverloadsMetric",
                    "store_values_type": "all",
                    "opendss_classes": ["Lines", "Transformers"],
                    "limits": [0, limits_max],
                }
             ]
        }

    @staticmethod
    def _get_window_sizes(inputs, resolution):
        line_window_size = timedelta(hours=inputs["line_window_size_hours"])
        if line_window_size % resolution != timedelta(0):
            raise InvalidConfiguration(
                f"line_window_size={line_window_size} must be a multiple of {resolution}"
            )
        transformer_window_size = timedelta(hours=inputs["transformer_window_size_hours"])
        if transformer_window_size % resolution != timedelta(0):
            raise InvalidConfiguration(
                f"transformer_window_size={transformer_window_size} must be a multiple of {resolution}"
            )
        return line_window_size, transformer_window_size

    @staticmethod
    def _get_required_exports_moving_average(inputs, resolution):
        line_window_size, transformer_window_size = ThermalMetrics._get_window_sizes(inputs, resolution)

        return {
            "CktElement": [
                {
                    "property": "ExportOverloadsMetric",
                    "store_values_type": "max",
                    "opendss_classes": ["Lines", "Transformers"]
                },
                {
                    "property": "ExportOverloadsMetric",
                    "opendss_classes": ["Lines", "Transformers"],
                    "store_values_type": "moving_average_max",
                    "window_sizes": {
                        "Lines": int(line_window_size / resolution),
                        "Transformers": int(transformer_window_size / resolution),
                    },
                },
            ],
        }

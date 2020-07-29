
from collections import defaultdict
from datetime import timedelta
import logging
import os

import pandas as pd

from PyDSS.common import StoreValuesType
from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.reports.reports import ReportBase, ReportGranularity
from PyDSS.utils.utils import dump_data


logger = logging.getLogger(__name__)


class VoltageMetrics(ReportBase):
    """Reports voltage metrics."""

    DEFAULTS = {
        "range_a_limits": [0.95, 1.05],
        "range_b_limits": [0.90, 1.0583],
        "window_size_minutes": 10,
    }
    FILENAME = "voltage_metrics.json"
    NAME = "Voltage Metrics"

    def __init__(self, name, results, simulation_config):
        super().__init__(name, results, simulation_config)
        assert len(results.scenarios) == 2
        self._granularity = ReportGranularity(self._report_global_options["Granularity"])
        self._range_a_limits = self._report_options["range_a_limits"]
        self._range_b_limits = self._report_options["range_b_limits"]
        self._resolution = self._get_simulation_resolution()
        inputs = self.get_inputs_from_defaults(self._simulation_config, self.NAME)
        self._store_type = self._get_store_type(inputs, self._resolution)
        self._prop_name = "VoltageMetric"
        if self._store_type == StoreValuesType.MOVING_AVERAGE:
            self._prop_name += "Avg"
        node_names1 = self._scenarios[0].list_element_names("Nodes", self._prop_name)
        node_names2 = self._scenarios[1].list_element_names("Nodes", self._prop_name)
        assert len(node_names1) == len(node_names2)
        self._node_names = node_names1

    def generate(self, output_dir):
        data = {
            "num_nodes": len(self._node_names),
            "metric_1": {},
            "metric_2": {},
            "metric_4": {},
            "metric_5": {},
            "metric_6": {},
        }
        dfs = {
            x.name: x.get_filtered_dataframes("Nodes", self._prop_name)
            for x in self._results.scenarios
        }
        for scenario in self._results.scenarios:
            name = scenario.name
            data["metric_1"][name] = self._gen_metric_1(name, dfs[name])
            data["metric_2"][name] = self._gen_metric_4(name, dfs[name], output_dir)
            data["metric_5"][name] = self._gen_metric_5(scenario, dfs[name])
        data["metric_6"] = self._gen_metric_6(dfs)
        self._export_json_report(data, output_dir, self.FILENAME)

    def _gen_metric_1(self, name, dfs):
        # This metric determines the total time points when any nodal voltage
        # in the feeder violates ANSI Range A voltage limits but all nodes in
        # the feeder are within ANSI Range B limits.
        results = {"time_points": []}
        if not dfs:
            return results

        node_violations = {}
        total_a = None
        total_b = None
        for df in dfs.values():
            series_a = df.applymap(self._one_if_violates_range_a_within_b).iloc[:, 0]
            series_b = df.applymap(self._one_if_violates_range_b).iloc[:, 0]
            if total_a is None:
                total_a = series_a
                total_b = series_b
            else:
                total_a = total_a.add(series_a, fill_value=0)
                total_b = total_b.add(series_b, fill_value=0)
        total_a.iloc[4] = 1
        total_b.iloc[4] = 0
        results["time_points"] = [
            str(ts) for ts, val in total_a.iteritems() if val > 0 and total_b.loc[ts] == 0
        ]
        results["duration"] = str(len(results["time_points"]) * self._resolution)
        return results

    def _gen_metric_4(self, scenario_name, dfs, output_dir):
        # Create a dataframe whose single column is a percentage of the number
        # of nodes experiencing violations at each time point.
        # Time points with no violations are not present in the dataframe.

        # Also create a dictionary of node name to range A violation count for
        # use in Metric 2.

        node_violations = {}
        total = None
        for node_name, df in dfs.items():
            series = df.applymap(self._one_if_violates_range_a).iloc[:, 0]
            node_violations[node_name] = series.sum()
            if total is None:
                total = series
            else:
                total = total.add(series, fill_value=0)

        if total is None:
            df = pd.DataFrame()
        else:
            total = total / len(self._node_names) * 100
            total.name = "Percent Node Violations Range A"
            df = pd.DataFrame(total)

        basename = f"voltage_metric_4__{scenario_name}"
        self._export_dataframe_report(df, output_dir, basename)
        return node_violations

    def _one_if_violates_range_a(self, val):
        return self._one_if_violates_limits(val, self._range_a_limits)

    def _one_if_violates_range_b(self, val):
        return self._one_if_violates_limits(val, self._range_b_limits)

    @staticmethod
    def _one_if_violates_limits(val, limits):
        return 1 if (val < limits[0] or val > limits[1]) else 0

    def _one_if_violates_range_a_within_b(self, val):
        limits_a = self._range_a_limits
        limits_b = self._range_b_limits
        if (val < limits_a[0] and val > limits_b[0]) or (val > limits_a[1] and val < limits_b[1]):
            return 1
        return 0

    def _gen_metric_5(self, scenario, dfs):
        if self._store_type == StoreValuesType.ALL:
            return self._gen_metric_5_all(dfs)
        return self._gen_metric_5_min_max(scenario)

    def _gen_metric_5_all(self, dfs):
        # Check the max and min voltages against the ANSI ranges.
        node_voltages = defaultdict(dict)
        num_outside_range_b = 0
        num_between_ranges = 0
        num_inside_range_a = 0
        overall_max = None
        overall_min = None
        for name, df in dfs.items():
            max_val = df.iloc[:, 0].max()
            min_val = df.iloc[:, 0].min()
            if min_val < self._range_b_limits[0] or max_val > self._range_b_limits[1]:
                num_outside_range_b += 1
            elif min_val < self._range_a_limits[0] or max_val > self._range_a_limits[1]:
                num_between_ranges += 1
            else:
                num_inside_range_a += 1
            overall_max, overall_min = self._get_new_max_min(
                node_voltages, name, max_val, min_val, overall_max, overall_min
            )

        return {
            "max_min_node_voltages": node_voltages,
            "num_outside_range_b": num_outside_range_b,
            "num_between_ranges": num_between_ranges,
            "num_inside_range_a": num_inside_range_a,
            "max_voltage": overall_max,
            "min_voltage": overall_min,
        }

    def _gen_metric_5_min_max(self, scenario):
        overall_max = None
        overall_min = None
        node_voltages = defaultdict(dict)
        for name in scenario.list_element_value_names("Nodes", "VoltageMetricMin"):
            max_val = scenario.get_element_property_value("Nodes", "VoltageMetricMax", name)
            min_val = scenario.get_element_property_value("Nodes", "VoltageMetricMin", name)
            overall_max, overall_min = self._get_new_max_min(
                node_voltages, name, max_val, min_val, overall_max, overall_min
            )

        return {
            "max_min_node_voltages": node_voltages,
            "max_voltage": overall_max,
            "min_voltage": overall_min,
        }

    @staticmethod
    def _get_new_max_min(node_voltages, name, max_val, min_val, overall_max, overall_min):
        node_voltages[name]["max"] = max_val
        node_voltages[name]["min"] = min_val
        if overall_max is None:
            overall_max = max_val
            overall_min = min_val
        else:
            if max_val > overall_max:
                overall_max = max_val
            if min_val < overall_min:
                overall_min = min_val
        return overall_max, overall_min

    def _gen_metric_6(self, dfs):
        pf1_time_points = self._gen_metric_6_violation_time_points(
            dfs[self._results.scenarios[0].name],
            self._results.scenarios[0],
        )
        cm_time_points = self._gen_metric_6_violation_time_points(
            dfs[self._results.scenarios[1].name],
            self._results.scenarios[1],
        )
        return {
            "num_time_points_violations_pf1": len(pf1_time_points),
            "num_time_points_violations_control_mode": len(cm_time_points),
        }

    def _gen_metric_6_violation_time_points(self, dfs, scenario):
        # Record number of time points with range B violations and compare to
        # baseline.
        violation_time_points = set()
        for df in dfs.values():
            violation_time_points.update(set(df.index.values))
        return violation_time_points

    @staticmethod
    def get_required_exports(simulation_config):
        resolution = timedelta(seconds=simulation_config["Project"]["Step resolution (sec)"])
        inputs = VoltageMetrics.get_inputs_from_defaults(simulation_config, VoltageMetrics.NAME)
        if inputs.get("force_instantaneous", False):
            data = VoltageMetrics._get_required_exports_instantaneous(inputs)
        elif inputs.get("force_moving_average", False):
            data = VoltageMetrics._get_required_exports_moving_average(inputs, resolution)
        elif resolution >= timedelta(minutes=15):
            data = VoltageMetrics._get_required_exports_instantaneous(inputs)
        else:
            data = VoltageMetrics._get_required_exports_moving_average(inputs, resolution)

        return data

    @staticmethod
    def _get_required_exports_instantaneous(inputs):
        return {
            "Nodes": [
                {
                    "property": "VoltageMetric",
                    "store_values_type": "all",
                    "limits": inputs["range_b_limits"],
                },
            ]
        }

    @staticmethod
    def _get_required_exports_moving_average(inputs, resolution):
        window_size_td = timedelta(minutes=inputs["window_size_minutes"])
        if window_size_td % resolution != timedelta(0):
            raise InvalidConfiguration(
                f"window_size_minutes={window_size_td} must be a multiple of {resolution}"
            )
        window_size = int(window_size_td / resolution)

        return {
            "Nodes": [
                {
                    "property": "VoltageMetric",
                    "store_values_type": "moving_average",
                    "limits": inputs["range_b_limits"],
                    "window_size": window_size,
                },
                {
                    "property": "VoltageMetric",
                    "store_values_type": "max",
                },
                {
                    "property": "VoltageMetric",
                    "store_values_type": "min",
                }
            ]
        }

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

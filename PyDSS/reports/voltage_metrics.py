
from collections import defaultdict
from datetime import timedelta
import logging

import pandas as pd

from PyDSS.common import StoreValuesType
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.reports.reports import ReportBase, ReportGranularity
from PyDSS.utils.utils import serialize_timedelta, deserialize_timedelta


logger = logging.getLogger(__name__)


class VoltageMetrics(ReportBase):
    """Reports voltage metrics.

    The metrics are defined in this paper:
    https://www.sciencedirect.com/science/article/pii/S0306261920311351

    The report generates the output file Reports/voltage_metrics.json.
    Metrics 1, 2, 5, and 6 are included within that file.

    Metric 3 must be read from the raw data as in the example below.
    Metric 4 must be read from the dataframe-as-binary-file.

    This example assumes that data is stored on a per-time-point basis.

    .. code-block:: python

        from PyDSS.utils.dataframe_utils import read_dataframe
        from PyDSS.pydss_results import PyDssResults

        results = PyDssResults("path_to_project")
        control_mode_scenario = results.scenarios[1]

        # Read metrics 1, 2, 5, and 6 directly from JSON.
        voltage_metrics = results.read_report("Voltage Metrics")
        metric_4_filenames = voltage_metrics["metric_4"]
        dfs = [read_dataframe(x) for x in filenames]

        # Read all metric 3 dataframes from raw data into memory in one call.
        dfs = control_mode_scenario.get_filtered_dataframes("Nodes", "VoltageMetric")

        # Read metric 3 dataframes into memory one at a time.
        for node_name in control_mode_scenario.list_element_names("Nodes", "VoltageMetric"):
            df = control_mode_scenario.get_dataframe("Nodes", "VoltageMetric", node_name)
            # If necessary, convert to a moving average with pandas.

    """
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
        
        self._window_size = int(
            timedelta(minutes=inputs["window_size_minutes"]) / self._resolution
        )
        
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
            "scenarios": [x.name for x in self._results.scenarios],
            "num_nodes": len(self._node_names),
            "metric_1": {},
            "metric_2": {},
            "metric_3": {},
            "metric_4": [],
            "metric_5": {},
            "metric_6": {},
            "summary": {},
        }
        dfs = {
            x.name: x.get_filtered_dataframes("Nodes", self._prop_name)
            for x in self._results.scenarios
        }
        for scenario in self._results.scenarios:
            name = scenario.name
            
            data["metric_1"][name] = self._gen_metric_1(name, dfs[name])
            data["metric_2"][name], output = self._gen_metric_4(name, dfs[name], output_dir)
            data["metric_3"][name] = self._gen_metric_3(name, dfs[name])
            data["metric_4"].append(output)
            data["metric_5"][name] = self._gen_metric_5(scenario, dfs[name])
        data["metric_6"] = self._gen_metric_6(dfs)
        
        data["summary"] = self._sumarize_metrics(data)

        # Note: metric 3 has to be read from the raw data. It is not duplicated
        # in the Reports directory.
        self._export_json_report(data, output_dir, self.FILENAME)

    def _gen_metric_1(self, name, dfs):
        # This metric determines the total time points when any nodal voltage
        # in the feeder violates ANSI Range A voltage limits but all nodes in
        # the feeder are within ANSI Range B limits.
        dur = timedelta(0)
        results = {
            "time_points": [],
            "duration": serialize_timedelta(dur)
        }
        if not dfs:
            return results

        
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
        results["time_points"] = [
            str(ts) for ts, val in total_a.iteritems() if val > 0 and total_b.loc[ts] == 0
        ]
        results["duration"] = str(len(results["time_points"]) * self._resolution)
        dur = len(results["time_points"]) * self._resolution
        results["duration"] = serialize_timedelta(dur)
        return results
    
    def _gen_metric_3(self, name, dfs):
        # This metric determines the total time points when any nodal moving average voltage
        # in the feeder violates ANSI Range A voltage limits.
        dur = timedelta(0)
        results = {
            "time_points": [],
            "duration": serialize_timedelta(dur)
        }
        if not dfs:
            return results
        
        total_a = None
        
        for df in dfs.values():
            df = df.rolling(self._window_size).mean()
            series_a = df.applymap(self._one_if_violates_range_a).iloc[:, 0]
            if total_a is None:
                total_a = series_a
                
            else:
                total_a = total_a.add(series_a, fill_value=0)
                
        results["time_points"] = [
            str(ts) for ts, val in total_a.iteritems() if val > 0 
        ]
        dur = len(results["time_points"]) * self._resolution
        results["duration"] = serialize_timedelta(dur)
        
        return results
    
    

    def _gen_metric_4(self, scenario_name, dfs, output_dir):
        # Create a dataframe whose single column is a percentage of the number
        # of nodes experiencing violations at each time point.
        # Time points with no violations are not present in the dataframe.

        # Also create a dictionary of node name to range A violation count for
        # use in Metric 2.

        # FUTURE: need to have a metric showing consecutive periods of violations.
        # Perhaps this could be the longest continuous range of violations for each node.
        node_violations = {}
        total = None
        num_steps = self._get_num_steps()
        for node_name, df in dfs.items():
            series = df.applymap(self._one_if_violates_range_a).iloc[:, 0]
            count = series.sum()
            dur = count * self._resolution
            node_violations[node_name] = {"duration": {}, "percentage": {}}
            node_violations[node_name]["duration"] = serialize_timedelta(dur)
            node_violations[node_name]["percentage"] = float(count / num_steps) * 100
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
        filename = self._export_dataframe_report(df, output_dir, basename)
        return node_violations, filename

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

    def _sumarize_metrics(self, data, scenario='control_mode'):
        
        voltage_metric_summary = {}
        num_time_points = self._get_num_steps()
        tot_dur = num_time_points * self._resolution
        moving_window_minutes = int(
            (self._window_size * self._resolution).total_seconds() / 60
        )
        
        if scenario in data['scenarios']:
            if data['metric_2'][scenario].values():
                max_pnvdoaa = max([x['duration'] for x in data['metric_2'][scenario].values()])
                max_pnvdoaa = deserialize_timedelta(max_pnvdoaa).total_seconds()
            else:
                max_pnvdoaa = 0
            
            vdbaab = deserialize_timedelta(data['metric_1'][scenario]['duration']).total_seconds()
            mmavdoa = deserialize_timedelta(data['metric_3'][scenario]['duration']).total_seconds()
            
            maxv = data['metric_5'][scenario]['max_voltage']
            
            if maxv is None:
                maxv = self._range_a_limits[1]
                
            minv = data['metric_5'][scenario]['min_voltage']
            if minv is None:
                minv = self._range_a_limits[1]
                
            voltage_metric_summary = {
                'voltage_duration_between_ansi_a_and_b-minutes': vdbaab / 60,
                'max_per_node_voltage_duration_outside_ansi_a-minutes': max_pnvdoaa / 60,
                 f'{moving_window_minutes}-minute_moving_average_voltage_duration_outside_ansi_a-minutes': mmavdoa / 60,
                'max_voltage': maxv,
                'min_voltage': minv,
                'num_nodes_always_inside_ansi_a': data['metric_5'][scenario]['num_inside_range_a'],
                'num_nodes_always_between_ansi_a_and_b': data['metric_5'][scenario]['num_between_ranges'],
                'num_nodes_always_outside_ansi_b': data['metric_5'][scenario]['num_outside_range_b'],
                'num_time_points_with_ansi_a_violations': data['metric_6'][f'num_time_points_violations_{scenario}'],
                'total_num_time_points': num_time_points,
                'total_simulation_duration': serialize_timedelta(tot_dur)
            }
            
        return voltage_metric_summary
        
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
                    "limits": inputs["range_a_limits"],
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
                    "limits": inputs["range_a_limits"],
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

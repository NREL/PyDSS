import os
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import logging

import pandas as pd

from PyDSS.common import StoreValuesType
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.reports.reports import ReportBase, ReportGranularity
from PyDSS.utils.utils import serialize_timedelta, deserialize_timedelta, load_data
from PyDSS.node_voltage_metrics import (
    SimulationVoltageMetricsModel,
    VoltageMetricsModel,
)


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
        self._granularity = ReportGranularity(
            self._report_global_options["Granularity"]
        )
        self._range_a_limits = self._report_options["range_a_limits"]
        self._range_b_limits = self._report_options["range_b_limits"]
        self._resolution = self._get_simulation_resolution()

    def generate(self, output_dir):
        # The generation code in this file has been deprecated in favor of the in-memory
        # collection in PyDSS/node_voltage_metrics.
        # Keeping this code around in case we want to make the behavior configurable.
        # The old code stores all violations, which could be useful.
        # data["summary"] = self._sumarize_metrics(data)

        metrics = {}
        for scenario in self._results.scenarios:
            filename = os.path.join(
                self._simulation_config["Project"]["Project Path"],
                self._simulation_config["Project"]["Active Project"],
                "Exports",
                scenario.name,
                self.FILENAME,
            )
            metrics[scenario.name] = VoltageMetricsModel(**load_data(filename))

        model = SimulationVoltageMetricsModel(scenarios=metrics)

        filename = os.path.join(output_dir, self.FILENAME)
        with open(filename, "w") as f_out:
            f_out.write(model.json())
            f_out.write("\n")

        logger.info("Generated %s", filename)

    @staticmethod
    def get_required_exports(simulation_config):
        inputs = VoltageMetrics.get_inputs_from_defaults(
            simulation_config, VoltageMetrics.NAME
        )
        return {
            "Nodes": [
                {
                    "property": "VoltageMetric",
                    "store_values_type": "all",
                    "limits": inputs["range_a_limits"],
                    "limits_b": inputs["range_b_limits"],
                },
            ]
        }

    @staticmethod
    def get_required_scenario_names():
        return set(["control_mode"])

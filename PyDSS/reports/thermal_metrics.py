
import logging
import os


from PyDSS.reports.reports import ReportBase
from PyDSS.thermal_metrics import SimulationThermalMetricsModel, ThermalMetricsSummaryModel
from PyDSS.utils.utils import load_data


logger = logging.getLogger(__name__)


class ThermalMetrics(ReportBase):
    """Reports thermal metrics.

    The metrics are defined in this paper:
    https://www.sciencedirect.com/science/article/pii/S0306261920311351

    The report generates the output file Reports/thermal_metrics.json.

    """

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

    def generate(self, output_dir):
        metrics = {}
        for scenario in self._results.scenarios:
            filename = os.path.join(
                self._simulation_config["Project"]["Project Path"],
                self._simulation_config["Project"]["Active Project"],
                "Exports",
                scenario.name,
                self.FILENAME,
            )
            metrics[scenario.name] = ThermalMetricsSummaryModel(**load_data(filename))

        model = SimulationThermalMetricsModel(scenarios=metrics)

        filename = os.path.join(output_dir, self.FILENAME)
        with open(filename, "w") as f_out:
            f_out.write(model.json(indent=2))
            f_out.write("\n")

        logger.info("Generated %s", filename)

    @staticmethod
    def get_required_exports(simulation_config):
        return {
            "CktElement": [
                {
                    "property": "ExportOverloadsMetricInMemory",
                    "store_values_type": "all",
                    "opendss_classes": ["Lines", "Transformers"],
                }
             ]
        }


    @staticmethod
    def get_required_scenario_names():
        return set(["control_mode"])

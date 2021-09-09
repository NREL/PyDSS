
import logging
import math
import os

from pydantic import BaseModel, Field

from PyDSS.reports.reports import ReportBase
from PyDSS.utils.utils import dump_data


logger = logging.getLogger(__name__)


class FeederLossesMetricsModel(BaseModel):
    """Data model for metrics describing feeder losses"""

    class Config:
        title = "FeederLossesMetricsModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False

    total_losses: float = Field(
        title="total_losses",
        description="Total losses in the circuit",
    )
    line_losses: float = Field(
        title="line_losses",
        description="Total line losses",
    )
    transformer_losses: float = Field(
        title="transformer_losses",
        description="Total transformer losses",
    )
    total_load_demand: float = Field(
        title="total_load_demand",
        description="Total power output of loads",
    )


def compare_feeder_losses(
        metrics1: FeederLossesMetricsModel,
        metrics2: FeederLossesMetricsModel,
        rel_tol=0.000001,
):
    """Compares the values of two instances of FeederLossesMetricsModel.

    Returns
    -------
    bool
        Return True if they match.

    """
    match = True
    for field in FeederLossesMetricsModel.__fields__:
        val1 = getattr(metrics1, field)
        val2 = getattr(metrics2, field)
        if not math.isclose(val1, val2, rel_tol=rel_tol):
            logger.error("field=%s mismatch %s : %s", field, val1, val2)
            match = False

    return match


class FeederLossesReport(ReportBase):
    """Reports the feeder losses.

    The report generates a feeder_losses.json output file.

    """

    FILENAME = "feeder_losses.json"
    NAME = "Feeder Losses"
    DEFAULTS = {
        "store_all_time_points": False,
    }

    def generate(self, output_dir):
        assert len(self._results.scenarios) >= 1
        scenario = self._results.scenarios[0]
        assert scenario.name == "control_mode"

        inputs = FeederLossesReport.get_inputs_from_defaults(self._simulation_config, self.NAME)
        if inputs["store_all_time_points"]:
            model = self._generate_from_all_time_points(scenario)
        else:
            model = self._generate_from_in_memory_metrics(scenario)

        filename = os.path.join(output_dir, self.FILENAME)
        with open(filename, "w") as f_out:
            f_out.write(model.json(indent=2))
            f_out.write("\n")
        logger.info("Generated %s", filename)
        return filename

    def _generate_from_in_memory_metrics(self, scenario):
        total_losses_dict = scenario.get_summed_element_total("Circuits", "LossesSum")
        total_losses = abs(next(iter(total_losses_dict.values()))) / 1000 # OpenDSS reports total losses in Watts
        line_losses_dict = scenario.get_summed_element_total("Circuits", "LineLossesSum")
        line_losses = abs(next(iter(line_losses_dict.values())))
        transformer_losses = total_losses - line_losses
        total_load_power_dict = scenario.get_summed_element_total("Loads", "PowersSum")
        total_load_power = 0
        for val in total_load_power_dict.values():
            total_load_power += val.real

        # TODO: total losses as a percentage of total load demand?
        return FeederLossesMetricsModel(
            total_losses=total_losses,
            line_losses=line_losses,
            transformer_losses=transformer_losses,
            total_load_demand=total_load_power,
        )

    def _generate_from_all_time_points(self, scenario):
        df_losses = scenario.get_full_dataframe("Circuits", "Losses")
        assert len(df_losses.columns) == 1

        df_line_losses = scenario.get_full_dataframe("Circuits", "LineLosses")
        assert len(df_line_losses.columns) == 1
        df_loads_powers = scenario.get_full_dataframe("Loads", "Powers")
        total_losses = abs(df_losses.sum().sum())
        line_losses = abs(df_line_losses.sum().sum())
        transformer_losses = total_losses - line_losses
        return FeederLossesMetricsModel(
            total_losses=total_losses,
            line_losses=line_losses,
            transformer_losses=transformer_losses,
            total_load_demand=df_loads_powers.sum().sum(),
        )

    @staticmethod
    def get_required_exports(simulation_config):
        inputs = FeederLossesReport.get_inputs_from_defaults(
            simulation_config, FeederLossesReport.NAME
        )
        if inputs["store_all_time_points"]:
            return {
                "Circuits": [
                    {
                        "property": "Losses",
                        "store_values_type": "all",
                    },
                    {
                        "property": "LineLosses",
                        "store_values_type": "all",
                    }
                ],
                "Loads": [
                    {
                        "property": "Powers",
                        "store_values_type": "all",
                        "data_conversion": "abs_sum",
                    },
                ]
            }

        return {
            "Circuits": [
                {
                    "property": "Losses",
                    "store_values_type": "sum",
                    "sum_elements": True,
                },
                {
                    "property": "LineLosses",
                    "store_values_type": "sum",
                    "sum_elements": True,
                }
            ],
            "Loads": [
                {
                    "property": "Powers",
                    "store_values_type": "sum",
                    "sum_elements": True,
                    "data_conversion": "abs_sum",
                },
            ]
        }

    @staticmethod
    def get_required_scenario_names():
        return set(["control_mode"])

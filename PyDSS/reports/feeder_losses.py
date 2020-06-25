
import logging
import os

from PyDSS.reports.reports import ReportBase
from PyDSS.utils.utils import dump_data


logger = logging.getLogger(__name__)


class FeederLossesReport(ReportBase):
    """Reports the feeder losses."""

    FILENAME = "feeder_losses.json"
    NAME = "Feeder Losses"

    def generate(self, output_dir):
        assert len(self._results.scenarios) == 2
        scenario = self._results.scenarios[1]
        total_losses_dict = scenario.get_summed_element_total("Circuits", "LossesSum")
        total_losses = abs(next(iter(total_losses_dict.values())))
        line_losses_dict = scenario.get_summed_element_total("Circuits", "LineLossesSum")
        line_losses = abs(next(iter(line_losses_dict.values())))
        transformer_losses = total_losses - line_losses
        total_load_power_dict = scenario.get_summed_element_total("Loads", "PowersSum")
        total_load_power = 0
        for val in total_load_power_dict.values():
            total_load_power += val.real

        data = {
            "total_losses": total_losses,
            "line_losses": line_losses,
            "tranformer_losses": transformer_losses,
            "total_load_demand": total_load_power,
            # TODO: total losses as a percentage of total load demand?
        }
        filename = os.path.join(output_dir, self.FILENAME)
        dump_data(data, filename, indent=2)
        logger.info("Generated %s", filename)
        return filename

    @staticmethod
    def get_required_exports(simulation_config):
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

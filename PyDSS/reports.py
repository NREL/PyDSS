"""Creates reports on data exported by PyDSS"""

import abc
import logging
import os

from PyDSS.exceptions import InvalidConfiguration, InvalidParameter
from PyDSS.utils.dataframe_utils import write_dataframe
from PyDSS.utils.utils import dump_data


REPORTS_DIR = "Reports"

logger = logging.getLogger(__name__)


class Reports:
    """Generate reports from a PyDSS project"""
    def __init__(self, results):
        self._results = results
        self._report_names = []
        self._report_options = results.simulation_config["Reports"]
        for report in self._report_options["Types"]:
            if report["enabled"]:
                self._report_names.append(report["name"])
        self._output_dir = os.path.join(results.project_path, REPORTS_DIR)
        os.makedirs(self._output_dir, exist_ok=True)

    @staticmethod
    def append_required_exports(exports, options):
        """Append export properties required by the configured reports.

        Parameters
        ----------
        exports : ExportListReader
        options : dict
            Simulation options

        """
        report_options = options.get("Reports")
        if report_options is None:
            return

        for report in report_options["Types"]:
            if not report["enabled"]:
                continue
            name = report["name"]
            if name not in REPORTS:
                raise InvalidConfiguration(f"{name} is not a valid report")

            required = REPORTS[name].get_required_reports()
            for elem_class, required_properties in required.items():
                for req_prop in required_properties:
                    found = False
                    store_type = req_prop["store_values_type"]
                    for prop in exports.list_element_properties(elem_class):
                        if prop.name == req_prop["property"] and \
                                prop.store_values_type.value == store_type:
                            found = True
                            break
                    if not found:
                        exports.append_property(elem_class, req_prop)
                        logger.debug("Add required property: %s %s", elem_class, req_prop)


    @classmethod
    def generate_reports(cls, results):
        """Generate all reports specified in the configuration.

        Parameters
        ----------
        results : PyDssResults

        Returns
        -------
        list
            list of report filenames

        """
        reports = Reports(results)
        return reports.generate()

    def generate(self):
        """Generate all reports specified in the configuration.

        Returns
        -------
        list
            list of report filenames

        """
        filenames = []
        for name in self._report_names:
            report = REPORTS[name](self._results, self._report_options)
            filename = report.generate(self._output_dir)
            filenames.append(filename)

        return filenames


class ReportBase(abc.ABC):
    """Base class for reports"""
    def __init__(self, results, report_options):
        self._results = results
        self._report_options = report_options

    @abc.abstractmethod
    def generate(self, output_dir):
        """Generate a report in output_dir.

        Returns
        -------
        str
            path to report

        """

    @staticmethod
    @abc.abstractmethod
    def get_required_reports():
        """Return the properties required for the report for export.

        Returns
        -------
        dict

        """

class PvClippingReport(ReportBase):
    """Reports PV Clipping for the simulation."""

    FILENAME = "pv_clipping.json"

    def __init__(self, results, report_options):
        super().__init__(results, report_options)
        assert len(results.scenarios) == 2
        self._pf1_scenario = results.scenarios[0]
        self._control_mode_scenario = results.scenarios[1]
        self._pv_system_names = self._control_mode_scenario.list_element_names("PVSystems")
        self._pf1_pv_systems = {
            x["name"]: x for x in self._pf1_scenario.read_pv_profiles()["pv_systems"]
        }
        self._control_mode_pv_systems = {
            x["name"]: x for x in self._control_mode_scenario.read_pv_profiles()["pv_systems"]
        }

    def _get_pv_system_info(self, pv_system, scenario):
        if scenario == "pf1":
            pv_systems = self._pf1_pv_systems
        else:
            pv_systems = self._control_mode_pv_systems

        return pv_systems[pv_system]

    def calculate_pv_clipping(self, pv_system):
        """Calculate PV clipping for one PV system.

        Returns
        -------
        int

        """
        cm_info = self._get_pv_system_info(pv_system, "control_mode")
        pmpp = cm_info["pmpp"]
        irradiance = cm_info["irradiance"]
        total_irradiance = cm_info["load_shape_pmult_sum"]
        annual_dc_power = pmpp * irradiance * total_irradiance
        pf1_real_power = self._pf1_scenario.get_dataframe(
            "PVSystems", "Powers", pv_system, real_only=True
        )
        annual_pf1_real_power = sum([abs(x) for x in pf1_real_power.sum()])
        clipping = annual_dc_power - annual_pf1_real_power
        logger.debug("PV clipping for %s = %s", pv_system, clipping)
        return clipping

    def generate(self, output_dir):
        data = {"pv_systems": []}
        for name in self._pv_system_names:
            clipping = {
                "name": name,
                "pv_clipping": self.calculate_pv_clipping(name),
            }
            data["pv_systems"].append(clipping)

        filename = os.path.join(output_dir, self.FILENAME)
        dump_data(data, filename, indent=2)
        logger.info("Generated PV Clipping report %s", filename)
        return filename

    @staticmethod
    def get_required_reports():
        return {
            "PVSystems": [
                {
                    "property": "Powers",
                    "store_values_type": "all",
                }
            ]
        }


class PvCurtailmentReport(ReportBase):
    """Reports PV Curtailment at every time point in the simulation."""

    FILENAME = "pv_curtailment"

    def __init__(self, results, report_options):
        super().__init__(results, report_options)
        assert len(results.scenarios) == 2
        self._pf1_scenario = results.scenarios[0]
        self._control_mode_scenario = results.scenarios[1]
        self._pv_system_names = self._control_mode_scenario.list_element_names("PVSystems")
        self._pf1_pv_systems = {
            x["name"]: x for x in self._pf1_scenario.read_pv_profiles()["pv_systems"]
        }
        self._control_mode_pv_systems = {
            x["name"]: x for x in self._control_mode_scenario.read_pv_profiles()["pv_systems"]
        }

    def _get_pv_system_info(self, pv_system, scenario):
        if scenario == "pf1":
            pv_systems = self._pf1_pv_systems
        else:
            pv_systems = self._control_mode_pv_systems

        return pv_systems[pv_system]

    def generate(self, output_dir):
        df = self.calculate_pv_curtailment()
        filename = os.path.join(
            output_dir,
            self.FILENAME
        ) + "." + self._report_options["Format"]
        write_dataframe(df, filename, compress=True)

        logger.info("Generated PV Clipping report %s", filename)
        return filename

    @staticmethod
    def get_required_reports():
        return {
            "PVSystems": [
                {
                    "property": "Powers",
                    "store_values_type": "all",
                }
            ]
        }

    def calculate_pv_curtailment(self):
        """Calculate PV curtailment for all PV systems.

        Returns
        -------
        pd.DataFrame

        """
        pf1_power = self._pf1_scenario.get_full_dataframe(
            "PVSystems", "Powers", real_only=True
        )
        control_mode_power = self._control_mode_scenario.get_full_dataframe(
            "PVSystems", "Powers", real_only=True
        )
        # TODO: needs work
        return (pf1_power - control_mode_power) / pf1_power * 100


class CapacitorStateChangeReport(ReportBase):
    """Reports the state changes per Capacitor."""

    FILENAME = "capacitor_state_changes.json"

    def generate(self, output_dir):
        data = {"scenarios": []}
        for scenario in self._results.scenarios:
            scenario_data = {"name": scenario.name, "capacitors": []}
            for capacitor in scenario.list_element_names("Capacitors"):
                try:
                    change_count = int(scenario.get_element_property_number(
                        "Capacitors", "TrackStateChanges", capacitor
                    ))
                except InvalidParameter:
                    change_count = 0
                changes = {"name": capacitor, "change_count": change_count}
                scenario_data["capacitors"].append(changes)
            data["scenarios"].append(scenario_data)

        filename = os.path.join(output_dir, self.FILENAME)
        dump_data(data, filename, indent=2)
        logger.info("Generated %s", filename)
        return filename

    @staticmethod
    def get_required_reports():
        return {
            "Capacitors": [
                {
                    "property": "TrackStateChanges",
                    "store_values_type": "change_count",
                }
            ]
        }


class RegControlTapNumberChangeReport(ReportBase):
    """Reports the tap number changes per RegControl."""

    FILENAME = "reg_control_tap_number_changes.json"

    def generate(self, output_dir):
        data = {"scenarios": []}
        for scenario in self._results.scenarios:
            scenario_data = {"name": scenario.name, "reg_controls": []}
            for reg_control in scenario.list_element_names("RegControls"):
                change_count = int(scenario.get_element_property_number(
                    "RegControls", "TrackTapNumberChanges", reg_control
                ))
                changes = {"name": reg_control, "change_count": change_count}
                scenario_data["reg_controls"].append(changes)
            data["scenarios"].append(scenario_data)

        filename = os.path.join(output_dir, self.FILENAME)
        dump_data(data, filename, indent=2)
        logger.info("Generated %s", filename)
        return filename

    @staticmethod
    def get_required_reports():
        return {
            "RegControls": [
                {
                    "property": "TrackTapNumberChanges",
                    "store_values_type": "change_count",
                }
            ]
        }


REPORTS = {
    "PV Clipping": PvClippingReport,
    "PV Curtailment": PvCurtailmentReport,
    "Capacitor State Change Counts": CapacitorStateChangeReport,
    "RegControl Tap Number Change Counts": RegControlTapNumberChangeReport,
}

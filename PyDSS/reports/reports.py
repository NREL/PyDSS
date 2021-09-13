"""Creates reports on data exported by PyDSS"""

from datetime import timedelta
import abc
import copy
import enum
import logging
import math
import os
import time

from PyDSS.common import DataConversion
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.utils.dataframe_utils import write_dataframe
from PyDSS.utils.simulation_utils import create_time_range_from_settings
from PyDSS.utils.utils import dump_data, make_json_serializable


REPORTS_DIR = "Reports"

logger = logging.getLogger(__name__)


class Reports:
    """Generate reports from a PyDSS project"""
    def __init__(self, results):
        self._results = results
        self._report_names = []
        self._simulation_config = results.simulation_config
        for report in results.simulation_config["Reports"]["Types"]:
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
        all_reports = Reports.get_all_reports()
        report_options = options.get("Reports")
        if report_options is None:
            return

        existing_scenarios = {x["name"] for x in options["Project"]["Scenarios"]}
        for report in report_options["Types"]:
            if not report["enabled"]:
                continue
            name = report["name"]
            if name not in all_reports:
                raise InvalidConfiguration(f"{name} is not a valid report")

            required_scenarios = all_reports[name].get_required_scenario_names()
            missing = required_scenarios.difference(existing_scenarios)
            if missing:
                text = " ".join(missing)
                raise InvalidConfiguration(f"{name} requires these scenarios: {text}")

            scenarios = report.get("scenarios")
            active_scenario = options["Project"]["Active Scenario"]
            if scenarios and active_scenario not in scenarios:
                logger.debug("report %s is not enabled for scenario %s", name,
                             active_scenario)
                continue

            required = all_reports[name].get_required_exports(options)
            for elem_class, required_properties in required.items():
                for req_prop in required_properties:
                    found = False
                    store_type = req_prop.get("store_values_type", "all")
                    for prop in exports.list_element_properties(elem_class):
                        if prop.name == req_prop["property"] and \
                                prop.store_values_type.value == store_type:
                            if prop.opendss_classes or req_prop.get("opendss_classes"):
                                assert prop.sum_elements == req_prop.get("sum_elements", False)
                                assert prop.data_conversion == \
                                    req_prop.get("data_conversion", DataConversion.NONE)
                                prop.append_opendss_classes(req_prop["opendss_classes"])
                            found = True
                    if not found:
                        exports.append_property(elem_class, req_prop)
                        logger.debug("Add required property: %s %s", elem_class, req_prop)

            all_reports[name].set_required_project_settings(options)

    @staticmethod
    def get_all_reports():
        reports = {}

        def append_reports(report_cls):
            subclasses = report_cls.__subclasses__()
            if subclasses:
                for cls in subclasses:
                    # Recurse.
                    append_reports(cls)
            else:
                reports[report_cls.NAME] = report_cls

        append_reports(ReportBase)
        return reports

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
        all_reports = self.get_all_reports()
        for name in self._report_names:
            report = all_reports[name](name, self._results, self._simulation_config)
            start = time.time()
            filename = report.generate(self._output_dir)
            duration = round(time.time() - start, 3)
            logger.info("Time to create %s report: %s seconds", name, duration)
            filenames.append(filename)

        return filenames


# Note to devs:  all subclasses of ReportBase need to reside in PyDSS/reports
# in order to be automatically imported. Otherwise, add a direct import in
# PyDSS/reports/__init__.py.

class ReportBase(abc.ABC):
    """Base class for reports"""
    def __init__(self, name, results, simulation_config):
        self._results = results
        self._scenarios = results.scenarios
        self._simulation_config = simulation_config
        self._report_global_options = simulation_config["Reports"]
        self._report_options = _get_report_options(simulation_config, name)

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
    def get_required_exports(simulation_config):
        """Return the properties required for the report for export.

        Parameters
        ----------
        simulation_config: dict
            settings from simulation config file

        Returns
        -------
        dict

        """

    @staticmethod
    @abc.abstractmethod
    def get_required_scenario_names():
        """Return the scenario names that the report expects to be able to retrieve.

        Returns
        -------
        set
            Set of strings

        """

    @staticmethod
    def get_inputs_from_defaults(simulation_config, name):
        all_reports = Reports.get_all_reports()
        options = _get_report_options(simulation_config, name)
        inputs = copy.deepcopy(getattr(all_reports[name], "DEFAULTS"))
        for key, val in options.items():
            inputs[key] = val

        return inputs

    @staticmethod
    def set_required_project_settings(simulation_config):
        """Make report-required changes to the simulation config.

        Parameters
        ----------
        simulation_config : dict
            Settings to be modified.

        """
        # Default behavior is no change.

    def _export_dataframe_report(self, df, output_dir, basename):
        """Export report to a dataframe."""
        fmt = self._report_global_options["Format"]
        filename = os.path.join(output_dir, basename + "." + fmt)
        compress = True if fmt == "h5" else False
        write_dataframe(df, filename, compress=compress)
        logger.info("Generated %s", filename)
        return filename

    def _export_json_report(self, data, output_dir, filename):
        """Export report to a JSON file."""
        filename = os.path.join(output_dir, filename)
        dump_data(data, filename, indent=2, default=make_json_serializable)
        logger.info("Generated %s", filename)

    def _get_simulation_resolution(self):
        res = self._simulation_config["Project"]["Step resolution (sec)"]
        return timedelta(seconds=res)

    def _get_num_steps(self):
        start, end, step = create_time_range_from_settings(self._simulation_config)
        return math.ceil((end - start) / step)

    @staticmethod
    def _params_from_granularity(granularity):
        if granularity == ReportGranularity.PER_ELEMENT_PER_TIME_POINT:
            store_values_type = "all"
            sum_elements = False
        elif granularity == ReportGranularity.PER_ELEMENT_TOTAL:
            store_values_type = "sum"
            sum_elements = False
        elif granularity == ReportGranularity.ALL_ELEMENTS_PER_TIME_POINT:
            store_values_type = "all"
            sum_elements = True
        elif granularity == ReportGranularity.ALL_ELEMENTS_TOTAL:
            store_values_type = "sum"
            sum_elements = True
        else:
            assert False, str(granularity)

        return store_values_type, sum_elements


class ReportGranularity(enum.Enum):
    """Specifies the granularity on which data is collected."""
    PER_ELEMENT_PER_TIME_POINT = "per_element_per_time_point"
    PER_ELEMENT_TOTAL = "per_element_total"
    ALL_ELEMENTS_PER_TIME_POINT = "all_elements_per_time_point"
    ALL_ELEMENTS_TOTAL = "all_elements_total"



def _get_report_options(simulation_config, name):
    for report in simulation_config["Reports"]["Types"]:
        if report["name"] == name:
            return report

    assert False, f"{name} is not present"

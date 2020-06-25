
import abc
import logging
import os

import pandas as pd

from PyDSS.common import PV_LOAD_SHAPE_FILENAME
from PyDSS.reports.reports import ReportBase, ReportGranularity
from PyDSS.utils.dataframe_utils import read_dataframe, write_dataframe
from PyDSS.utils.utils import dump_data


logger = logging.getLogger(__name__)


class PvReportBase(ReportBase, abc.ABC):
    """Base class for PV reports"""
    def __init__(self, name, results, simulation_config):
        super().__init__(name, results, simulation_config)
        assert len(results.scenarios) == 2
        self._pf1_scenario = results.scenarios[0]
        self._control_mode_scenario = results.scenarios[1]
        names = self._control_mode_scenario.list_element_names("ExportPowersMetric")
        cm_profiles = self._control_mode_scenario.read_pv_profiles()["pv_systems"]
        self._pv_system_names = [x["name"] for x in cm_profiles]
        self._pf1_pv_systems = {
            x["name"]: x for x in self._pf1_scenario.read_pv_profiles()["pv_systems"]
        }
        self._control_mode_pv_systems = {
            x["name"]: x for x in cm_profiles
        }

    def _get_pv_system_info(self, pv_system, scenario):
        if scenario == "pf1":
            pv_systems = self._pf1_pv_systems
        else:
            pv_systems = self._control_mode_pv_systems

        return pv_systems[pv_system]

    @staticmethod
    def get_required_exports(simulation_config):
        granularity = ReportGranularity(simulation_config["Reports"]["Granularity"])
        _type, sum_elements = ReportBase._params_from_granularity(granularity)
        return {
            "CktElement": [
                {
                    "property": "ExportPowersMetric",
                    "store_values_type": _type,
                    "opendss_classes": ["PVSystems"],
                    "sum_elements": sum_elements,
                },
            ],
        }


class PvClippingReport(PvReportBase):
    """Reports PV Clipping for the simulation."""

    PER_TIME_POINT_FILENAME = "pv_clipping.h5"
    TOTAL_FILENAME = "pv_clipping.json"
    NAME = "PV Clipping"

    def _generate_per_pv_system_per_time_point(self, pv_load_shapes, output_dir):
        data = {}
        index = None
        for name in self._pv_system_names:
            cm_info = self._get_pv_system_info(name, "control_mode")
            dc_power_per_time_point = pv_load_shapes[cm_info["load_shape_profile"]]
            pf1_real_power = self._pf1_scenario.get_dataframe("CktElement", "ExportPowersMetric", name)
            if index is None:
                index = pf1_real_power.index
            if len(dc_power_per_time_point) > len(pf1_real_power):
                dc_power_per_time_point = dc_power_per_time_point[:len(pf1_real_power)]
            clipping = dc_power_per_time_point - pf1_real_power.values[0]
            data[name] = clipping.values

        df = pd.DataFrame(data, index=index)
        filename = os.path.join(output_dir, self.PER_TIME_POINT_FILENAME)
        write_dataframe(df, filename, compress=True)

    def _generate_per_pv_system_total(self, output_dir):
        data = {"pv_systems": []}
        for name in self._pv_system_names:
            cm_info = self._get_pv_system_info(name, "control_mode")
            pmpp = cm_info["pmpp"]
            irradiance = cm_info["irradiance"]
            total_irradiance = cm_info["load_shape_pmult_sum"]
            annual_dc_power = pmpp * irradiance * total_irradiance
            pf1_real_power = self._pf1_scenario.get_element_property_value(
                "CktElement", "ExportPowersMetricSum", name
            )
            clipping = annual_dc_power - pf1_real_power
            data["pv_systems"].append(
                {
                    "name": name,
                    "clipping": clipping,
                }
            )

        filename = os.path.join(output_dir, self.TOTAL_FILENAME)
        dump_data(data, filename, indent=2)

    def _generate_all_pv_systems_per_time_point(self, pv_load_shapes, output_dir):
        pf1_real_power = self._pf1_scenario.get_summed_element_dataframe(
            "CktElement", "ExportPowersMetric"
        )
        # TODO: do we need to verify that there are no extra pv systems?
        dc_power_per_time_point = []
        for _, row in pv_load_shapes.iterrows():
            dc_power_per_time_point.append(row.sum())
            if len(dc_power_per_time_point) == len(pf1_real_power):
                break
        clipping = pd.DataFrame(
            dc_power_per_time_point - pf1_real_power.values[0],
            index=pf1_real_power.index,
            columns=["Clipping"],
        )
        filename = os.path.join(output_dir, self.PER_TIME_POINT_FILENAME)
        write_dataframe(clipping, filename, compress=True)

    def _generate_all_pv_systems_total(self, output_dir):
        annual_dc_power = 0.0
        for name in self._pv_system_names:
            cm_info = self._get_pv_system_info(name, "control_mode")
            pmpp = cm_info["pmpp"]
            irradiance = cm_info["irradiance"]
            total_irradiance = cm_info["load_shape_pmult_sum"]
            annual_dc_power += pmpp * irradiance * total_irradiance

        ac_power = next(iter(
            self._pf1_scenario.get_summed_element_total("CktElement", "ExportPowersMetricSum").values()
        ))
        # TODO: abs?
        clipping = annual_dc_power - ac_power
        data = {"clipping": clipping}
        filename = os.path.join(output_dir, self.TOTAL_FILENAME)
        dump_data(data, filename, indent=2)

    def _read_pv_load_shapes(self):
        path = os.path.join(
            self._simulation_config["Project"]["Project Path"],
            self._simulation_config["Project"]["Active Project"],
            "Exports",
            "control_mode",
            PV_LOAD_SHAPE_FILENAME,
        )
        return read_dataframe(path)

    def generate(self, output_dir):
        granularity = ReportGranularity(self._simulation_config["Reports"]["Granularity"])
        per_time_point = (
            ReportGranularity.PER_ELEMENT_PER_TIME_POINT,
            ReportGranularity.ALL_ELEMENTS_PER_TIME_POINT,
        )
        if granularity in per_time_point:
            pv_load_shapes = self._read_pv_load_shapes()
        else:
            pv_load_shapes = None

        if granularity == ReportGranularity.PER_ELEMENT_PER_TIME_POINT:
            self._generate_per_pv_system_per_time_point(pv_load_shapes, output_dir)
        elif granularity == ReportGranularity.PER_ELEMENT_TOTAL:
            self._generate_per_pv_system_total(output_dir)
        elif granularity == ReportGranularity.ALL_ELEMENTS_PER_TIME_POINT:
            self._generate_all_pv_systems_per_time_point(pv_load_shapes, output_dir)
        elif granularity == ReportGranularity.ALL_ELEMENTS_TOTAL:
            self._generate_all_pv_systems_total(output_dir)
        else:
            assert False


class PvCurtailmentReport(PvReportBase):
    """Reports PV Curtailment at every time point in the simulation."""

    PER_TIME_POINT_FILENAME = "pv_curtailment.h5"
    TOTAL_FILENAME = "pv_curtailment.json"
    NAME = "PV Curtailment"

    def _generate_per_pv_system_per_time_point(self, output_dir):
        pf1_power = self._pf1_scenario.get_full_dataframe("CktElement", "ExportPowersMetric")
        control_mode_power = self._control_mode_scenario.get_full_dataframe(
            "CktElement", "ExportPowersMetric"
        )
        df = (pf1_power - control_mode_power) / pf1_power * 100
        filename = os.path.join(output_dir, self.PER_TIME_POINT_FILENAME)
        write_dataframe(df, filename, compress=True)

    def _generate_per_pv_system_total(self, output_dir):
        data = {"pv_systems": []}
        for name in self._pv_system_names:
            pf1_power = self._pf1_scenario.get_element_property_value(
                "CktElement", "ExportPowersMetricSum", name
            )
            control_mode_power = self._control_mode_scenario.get_element_property_value(
                "CktElement", "ExportPowersMetricSum", name
            )
            curtailment = (pf1_power - control_mode_power) / pf1_power * 100
            data["pv_systems"].append(
                {
                    "name": name,
                    "curtailment": curtailment,
                }
            )

        filename = os.path.join(output_dir, self.TOTAL_FILENAME)
        dump_data(data, filename, indent=2)

    def _generate_all_pv_systems_per_time_point(self, output_dir):
        pf1_power = self._pf1_scenario.get_summed_element_dataframe("CktElement", "ExportPowersMetric")
        control_mode_power = self._control_mode_scenario.get_summed_element_dataframe(
            "CktElement", "ExportPowersMetric"
        )
        df = (pf1_power - control_mode_power) / pf1_power * 100
        filename = os.path.join(output_dir, self.PER_TIME_POINT_FILENAME)
        write_dataframe(df, filename, compress=True)

    def _generate_all_pv_systems_total(self, output_dir):
        pf1_power = next(iter(
            self._pf1_scenario.get_summed_element_total("CktElement", "ExportPowersMetricSum").values()
        ))
        control_mode_power = next(iter(
            self._control_mode_scenario.get_summed_element_total("CktElement", "ExportPowersMetricSum").values()
        ))

        curtailment = (pf1_power - control_mode_power) / pf1_power * 100
        data = {"curtailment": curtailment}
        filename = os.path.join(output_dir, self.TOTAL_FILENAME)
        dump_data(data, filename, indent=2)

    def generate(self, output_dir):
        granularity = ReportGranularity(self._simulation_config["Reports"]["Granularity"])
        if granularity == ReportGranularity.PER_ELEMENT_PER_TIME_POINT:
            self._generate_per_pv_system_per_time_point(output_dir)
        elif granularity == ReportGranularity.PER_ELEMENT_TOTAL:
            self._generate_per_pv_system_total(output_dir)
        elif granularity == ReportGranularity.ALL_ELEMENTS_PER_TIME_POINT:
            self._generate_all_pv_systems_per_time_point(output_dir)
        elif granularity == ReportGranularity.ALL_ELEMENTS_TOTAL:
            self._generate_all_pv_systems_total(output_dir)
        else:
            assert False

    def calculate_pv_curtailment(self):
        """Calculate PV curtailment for all PV systems.

        Returns
        -------
        pd.DataFrame

        """
        pf1_power = self._pf1_scenario.get_full_dataframe(
            "CktElement", "ExportPowersMetric", real_only=True
        )
        control_mode_power = self._control_mode_scenario.get_full_dataframe(
            "CktElement", "ExportPowersMetric", real_only=True
        )
        # TODO: needs work
        return (pf1_power - control_mode_power) / pf1_power * 100

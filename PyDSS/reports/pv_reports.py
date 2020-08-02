
import abc
import logging
import math
import os
import time

import numpy as np
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
        names = self._control_mode_scenario.list_element_names("Powers")
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
            "PVSystems": [
                {
                    "property": "Powers",
                    "store_values_type": _type,
                    "sum_elements": sum_elements,
                    "data_conversion": "sum_abs_real",
                },
            ],
        }


class PvClippingReport(PvReportBase):
    """Reports PV Clipping for the simulation."""

    PER_TIME_POINT_FILENAME = "pv_clipping.h5"
    TOTAL_FILENAME = "pv_clipping.json"
    NAME = "PV Clipping"

    @staticmethod
    def _calculate_clipping(total_dc_power, pf1_real_power):
        return (total_dc_power - pf1_real_power) * 100 / pf1_real_power

    @staticmethod
    def _calculate_clipping_array(dc_power, pf1_real_power):
        dcp = dc_power.values
        rp = pf1_real_power.values
        return (dcp - rp) * 100 / rp

    def _get_total_dc_power_across_pv_systems(self):
        total_dc_power = 0.0
        for name in self._pv_system_names:
            total_dc_power += self._get_total_dc_power(name)
        return total_dc_power

    def _get_total_dc_power(self, pv_system):
        cm_info = self._get_pv_system_info(pv_system, "control_mode")
        pmpp = cm_info["pmpp"]
        irradiance = cm_info["irradiance"]
        total_irradiance = cm_info["load_shape_pmult_sum"]
        return pmpp * irradiance * total_irradiance

    def _generate_per_pv_system_per_time_point(self, output_dir):
        data = {}
        pv_load_shapes = self._read_pv_load_shapes()
        pf1_real_power_full = self._pf1_scenario.get_full_dataframe(
            "PVSystems", "Powers"
        )

        # This can divide by 0.
        old_settings = np.seterr(divide='ignore', invalid='ignore')
        for name in self._pv_system_names:
            cm_info = self._get_pv_system_info(name, "control_mode")
            pf1_real_power = pf1_real_power_full[name + "__Powers"]
            dc_power = pv_load_shapes[cm_info["load_shape_profile"]] * \
                cm_info["pmpp"] * \
                cm_info["irradiance"]
            assert len(dc_power) == len(pf1_real_power), \
                f"{len(dc_power)} {len(pf1_real_power)}"
            clipping = self._calculate_clipping_array(dc_power, pf1_real_power)
            data[name] = clipping

        df = pd.DataFrame(data, index=pf1_real_power_full.index)
        self._export_dataframe_report(df, output_dir, "pv_clipping")
        np.seterr(**old_settings)

    def _generate_per_pv_system_total(self, output_dir):
        data = {"pv_systems": []}
        for name in self._pv_system_names:
            pf1_real_power = self._pf1_scenario.get_element_property_value(
                "PVSystems", "PowersSum", name
            )
            dc_power = self._get_total_dc_power(name)
            clipping = self._calculate_clipping(dc_power, pf1_real_power)
            data["pv_systems"].append(
                {
                    "name": name,
                    "clipping": clipping,
                }
            )
        self._export_json_report(data, output_dir, self.TOTAL_FILENAME)

    def _generate_all_pv_systems_per_time_point(self, output_dir):
        pf1_real_power = self._pf1_scenario.get_summed_element_dataframe(
            "PVSystems", "Powers"
        )
        pv_load_shapes = self._read_pv_load_shapes()
        dc_powers = {}
        for name in self._pv_system_names:
            cm_info = self._get_pv_system_info(name, "control_mode")
            series = pv_load_shapes[cm_info["load_shape_profile"]]
            dc_power = series * cm_info["pmpp"] * cm_info["irradiance"]
            assert len(dc_power) == len(pf1_real_power)
            dc_powers[name] = dc_power.values
            # TODO: just for validation
            assert math.isclose(sum(dc_power.values), cm_info["load_shape_pmult_sum"] * cm_info["pmpp"] * cm_info["irradiance"])
        df = pd.DataFrame(dc_powers, index=pf1_real_power.index)
        total_dc_power = df.sum(axis=1)

        clipping = pd.DataFrame(
            self._calculate_clipping_array(total_dc_power, pf1_real_power.iloc[:, 0]),
            index=pf1_real_power.index,
            columns=["TotalClipping"],
        )
        self._export_dataframe_report(clipping, output_dir, "pv_clipping")

    def _generate_all_pv_systems_total(self, output_dir):
        total_dc_power = self._get_total_dc_power_across_pv_systems()

        pf1_real_power = next(iter(
            self._pf1_scenario.get_summed_element_total("PVSystems", "PowersSum").values()
        ))
        clipping = self._calculate_clipping(total_dc_power, pf1_real_power)
        data = {"clipping": clipping}
        self._export_json_report(data, output_dir, self.TOTAL_FILENAME)

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


class PvCurtailmentReport(PvReportBase):
    """Reports PV Curtailment at every time point in the simulation."""

    PER_TIME_POINT_FILENAME = "pv_curtailment.h5"
    TOTAL_FILENAME = "pv_curtailment.json"
    NAME = "PV Curtailment"

    def _generate_per_pv_system_per_time_point(self, output_dir):
        pf1_power = self._pf1_scenario.get_full_dataframe("PVSystems", "Powers")
        control_mode_power = self._control_mode_scenario.get_full_dataframe(
            "PVSystems", "Powers"
        )
        df = (pf1_power - control_mode_power) / pf1_power * 100
        df.columns = [x.replace("Powers", "Curtailment") for x in df.columns]
        self._export_dataframe_report(df, output_dir, "pv_curtailment")

    def _generate_per_pv_system_total(self, output_dir):
        data = {"pv_systems": []}
        for name in self._pv_system_names:
            pf1_power = self._pf1_scenario.get_element_property_value(
                "PVSystems", "PowersSum", name
            )
            control_mode_power = self._control_mode_scenario.get_element_property_value(
                "PVSystems", "PowersSum", name
            )
            curtailment = (pf1_power - control_mode_power) / pf1_power * 100
            data["pv_systems"].append(
                {
                    "name": name,
                    "curtailment": curtailment,
                }
            )
        self._export_json_report(data, output_dir, self.TOTAL_FILENAME)

    def _generate_all_pv_systems_per_time_point(self, output_dir):
        pf1_power = self._pf1_scenario.get_summed_element_dataframe("PVSystems", "Powers")
        control_mode_power = self._control_mode_scenario.get_summed_element_dataframe(
            "PVSystems", "Powers"
        )
        df = (pf1_power - control_mode_power) / pf1_power * 100
        self._export_dataframe_report(df, output_dir, "pv_curtailment")

    def _generate_all_pv_systems_total(self, output_dir):
        pf1_power = next(iter(
            self._pf1_scenario.get_summed_element_total("PVSystems", "PowersSum").values()
        ))
        control_mode_power = next(iter(
            self._control_mode_scenario.get_summed_element_total("PVSystems", "PowersSum").values()
        ))

        curtailment = (pf1_power - control_mode_power) / pf1_power * 100
        data = {"curtailment": curtailment}
        self._export_json_report(data, output_dir, self.TOTAL_FILENAME)

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
            "PVSystems", "Powers", real_only=True
        )
        control_mode_power = self._control_mode_scenario.get_full_dataframe(
            "PVSystems", "Powers", real_only=True
        )
        return (pf1_power - control_mode_power) / pf1_power * 100

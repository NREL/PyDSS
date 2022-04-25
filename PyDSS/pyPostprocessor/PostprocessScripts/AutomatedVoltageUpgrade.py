#**Authors:**
# Akshay Kumar Jain; Akshay.Jain@nrel.gov

import os
import matplotlib.pyplot as plt
import opendssdirect as dss
import networkx as nx
import time
import numpy as np
try:
    import seaborn as sns
    _SEABORN_IMPORTED = True
except ImportError:
    _SEABORN_IMPORTED = False
import re
from sklearn.cluster import AgglomerativeClustering
import json
import math

from PyDSS.common import SimulationType
from PyDSS.exceptions import InvalidParameter, OpenDssConvergenceError
from PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
from PyDSS.pyPostprocessor.PostprocessScripts.postprocess_voltage_upgrades import postprocess_voltage_upgrades
from PyDSS.utils.dss_utils import iter_elements, check_redirect

plt.rcParams.update({'font.size': 14})


# to get metadata: source bus, substation xfmr information
def get_ckt_info():
    data_dict = {}
    dss.Vsources.First()
    source_bus = dss.CktElement.BusNames()[0].split(".")[0]
    data_dict['source_bus'] = source_bus
    dss.Transformers.First()
    while True:
        bus_names = dss.CktElement.BusNames()
        bus_names_only = []
        for buses in bus_names:
            bus_names_only.append(buses.split(".")[0].lower())
        if source_bus.lower() in bus_names_only:
            sub_xfmr = dss.Transformers.Name()
            data_dict["substation_xfmr"] = {
                "xfmr_name": sub_xfmr,
                "xfmr_kva": dss.Transformers.kVA(),
                "xfmr_kv": dss.Transformers.kV(),
                "bus_names": bus_names_only
            }
        if not dss.Transformers.Next() > 0:
            break
    return data_dict


# function to get regulator information
def get_reg_control_info():
    reg_name = dss.RegControls.Name()
    data_dict = {"name": reg_name, "xfmr_name": dss.RegControls.Transformer(),
                 "ptratio": dss.RegControls.PTRatio(),
                 "delay": dss.RegControls.Delay()}
    dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_name))
    data_dict["v_setpoint"] = dss.Properties.Value("vreg"),  # this returns a tuple - account in pp
    data_dict["v_deadband"] = dss.Properties.Value("band"),  # this returns a tuple - account in pp
    data_dict["enabled"] = dss.CktElement.Enabled(),  # this returns a tuple - account in postprocess
    data_dict["reg_bus"] = dss.CktElement.BusNames()[0].split(".")[0]
    dss.Circuit.SetActiveBus(data_dict["reg_bus"])
    data_dict["bus_num_phases"] = dss.CktElement.NumPhases()
    data_dict["bus_kv"] = dss.Bus.kVBase()
    dss.Circuit.SetActiveElement("Transformer.{}".format(data_dict["xfmr_name"]))
    data_dict["xfmr_kva"] = float(dss.Properties.Value("kva"))
    dss.Transformers.Wdg(1)  # setting winding to 1, to get kV for winding 1
    data_dict["xfmr_kv"] = dss.Transformers.kV()
    data_dict["xfmr_bus1"] = dss.CktElement.BusNames()[0].split(".")[0]
    data_dict["xfmr_bus2"] = dss.CktElement.BusNames()[1].split(".")[0]
    return data_dict


# function to get capacitor information
def get_capacitor_info():
    return {"name": dss.Capacitors.Name(), "kv": dss.Capacitors.kV(), "kvar": dss.Capacitors.kvar()}


def get_cap_controls_info():
    ctrl_name = dss.CapControls.Name()
    dss.Circuit.SetActiveElement("CapControl.{}".format(ctrl_name)) ##
    data_dict = {
            "name": ctrl_name,
            "cap_name": dss.CapControls.Capacitor(),
            "offsetting": dss.CapControls.OFFSetting(),
            "onsetting": dss.CapControls.ONSetting(),
            "control_type": dss.Properties.Value("type"),
            "ctratio": dss.CapControls.CTRatio(),
            "ptratio": dss.CapControls.PTRatio(),
        }
    dss.Capacitors.Name(data_dict["cap_name"])
    data_dict["cap_kvar"] = dss.Capacitors.kvar()
    data_dict["cap_kv"] = dss.Capacitors.kV()
    return data_dict


class AutomatedVoltageUpgrade(AbstractPostprocess):
    """
    This class is used to determine Voltage Upgrades
    """

    REQUIRED_INPUT_FIELDS = (
        "target_v",
        "initial_voltage_upper_limit",
        "initial_voltage_lower_limit",
        "final_voltage_upper_limit",
        "final_voltage_lower_limit",
        "nominal_voltage",
        "nominal_pu_voltage",
        "tps_to_test",
        "create_topology_plots",
        "cap_sweep_voltage_gap",
        "reg_control_bands",
        "reg_v_delta",
        "max_regulators",
        "use_ltc_placement",
        "thermal_scenario_name",
    )

    def __init__(self, project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
        """Constructor method
        """
        super(AutomatedVoltageUpgrade, self).__init__(project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger)
        self._simulation = None
        self._step = None
        dss = dssInstance
        self.dssSolver = dssSolver
        self.config["project_dss_files_path"] = project.dss_files_path
        self.config["thermal_scenario_path"] = project.get_post_process_directory(self.config["thermal_scenario_name"])

        if simulationSettings.project.simulation_type != SimulationType.SNAPSHOT:
            raise InvalidParameter("Upgrade post-processors are only supported on Snapshot simulations")

    def _run(self):
        # Just send this list as input to the upgrades code via DISCO -  this list may be empty or have as many
        # paths as the user desires - if empty the mults in the 'tps_to_test' input will be used else if non-empty
        # max and min load mults from the load.dss files will be used. Tne tps to test input should always be specified
        # irrespective of whether it gets used or not

        # these parameters are used only if multiple load and pv files are present
        # TODO: only fixed_tps (using tps_to_test list from config) works in this version
        #  associated function to compute violations need to be changed to make the multiple dss files option work
        use_fixed_tps = True
        if not use_fixed_tps:
            self.other_pv_dss_files = self.config["project_data"]["pydss_other_pvs_dss_files"]
            self.other_load_dss_files = self.config["project_data"]["pydss_other_loads_dss_files"]
            self.get_load_pv_mults_individual_object()  # multipliers are computed for individual load and pv
            # self.get_load_mults()  # max and min are taken
        else:
            self.other_load_dss_files = []
            self.other_pv_dss_files = []

        thermal_filename = "thermal_upgrades.dss"
        thermal_dss_file = os.path.join(self.config["thermal_scenario_path"], thermal_filename)
        self.logger.info("thermal_dss_file=%s", thermal_dss_file)
        if not os.path.exists(thermal_dss_file):
            raise InvalidParameter(f"AutomatedThermalUpgrade did not produce thermal_filename")
        check_redirect(thermal_dss_file)

        self.start = time.time()

        # reading original objects (before upgrades)
        self.orig_ckt_info = get_ckt_info()
        self.orig_reg_controls = {x["name"]: x for x in iter_elements(dss.RegControls, get_reg_control_info)}
        self.orig_capacitors = {x["name"]: x for x in iter_elements(dss.Capacitors, get_capacitor_info)}
        self.orig_capcontrols = {x["name"]: x for x in iter_elements(dss.CapControls, get_cap_controls_info)}
        self.orig_xfmr_info = dss.Transformers.AllNames()

        # Get feeder head meta data
        self.feeder_head_name = dss.Circuit.Name()
        self.feeder_head_bus = dss.CktElement.BusNames()[0].split(".")[0]
        dss.Circuit.SetActiveBus(self.feeder_head_bus)
        self.feeder_head_basekv = dss.Bus.kVBase()
        num_nodes = dss.Bus.NumNodes()
        if num_nodes > 1:
            self.feeder_head_basekv = round(self.feeder_head_basekv * math.sqrt(3), 1)

        # Cap bank default settings -
        self.capON = round((self.config["nominal_voltage"] - self.config["cap_sweep_voltage_gap"] / 2), 1)
        self.capOFF = round((self.config["nominal_voltage"] + self.config["cap_sweep_voltage_gap"] / 2), 1)
        self.capONdelay = 0
        self.capOFFdelay = 0
        self.capdeadtime = 0
        self.PTphase = "AVG"
        self.cap_control = "voltage"
        self.max_regs = self.config["max_regulators"]
        self.terminal = 1
        self.plot_violations_counter = 0
        # TODO: Regs default settings

        # Substation LTC default settings
        self.LTC_setpoint = 1.03 * self.config["nominal_voltage"]
        self.LTC_wdg = 2
        self.LTC_delay = 45  # in seconds
        self.LTC_band = 2  # deadband in volts

        self.place_new_regulators = False  # flag to determine whether to place new regulators or not

        # Initialize dss upgrades file
        self.dss_upgrades = [
            "//This file has all the upgrades determined using the control device placement algorithm \n"]

        self.dssSolver = dss.Solution

        # Get correct source bus and conn type for all downstream regs - since regs are added before DTs and after
        # sub xfmr - their connection should be same as that of secondary wdg of sub xfmr
        dss.Vsources.First()
        self.source = dss.CktElement.BusNames()[0].split(".")[0]
        self.reg_conn = "wye"
        dss.Transformers.First()
        while True:
            xfmr_buses = dss.CktElement.BusNames()
            for bus in xfmr_buses:
                if bus.split(".")[0].lower() == self.source:
                    num_wdgs = dss.Transformers.NumWindings()
                    for wdg in range(0, num_wdgs, 1):
                        self.reg_conn = dss.Properties.Value("conn")
            if not dss.Transformers.Next() > 0:
                break

        self.start_t = time.time()  # used to determine time taken for run
        self.generate_nx_representation()

        self.get_existing_controller_info()
        if self.config["create_topology_plots"]:
            self.plot_feeder()
            pass
        self.write_flag = 1
        self.feeder_parameters = {}

        self.create_result_comparison_voltages(comparison_stage='Before Upgrades')

        self.initial_buses_with_violations = self.buses_with_violations  # save initial bus violations
        self.upgrade_status = ''  # status - whether voltage upgrades done or not
        # if there are no buses with violations based on initial check, don't get into upgrade process
        # directly go to end of file
        if len(self.buses_with_violations) <= 0:
            self.logger.info("No Voltage Upgrades Required.")
            self.upgrade_status = 'No Voltage Upgrades needed'  # status - whether voltage upgrades done or not

        # else, if there are bus violations based on initial check, start voltage upgrades process
        else:
            # change voltage checking thresholds
            self.upper_limit = self.config["final_voltage_upper_limit"]
            self.lower_limit = self.config["final_voltage_lower_limit"]

            self.upgrade_status = 'Voltage Upgrades were needed'  # status - whether voltage upgrades done or not
            self.logger.info("Voltage Upgrades Required.")
            # Use this block for capacitor settings
            if len(self.buses_with_violations) > 0:
                if self.config["create_topology_plots"]:
                    self.plot_violations()
                # Correct cap banks settings if caps are present in the feeder
                if dss.Capacitors.Count() > 0:
                    self.logger.info("Cap bank settings sweep, if capacitors are present.")
                    self.get_capacitor_state()
                    self.correct_cap_bank_settings()
                    if self.config["create_topology_plots"]:
                        self.plot_violations()
                    if len(self.buses_with_violations) > 0:
                        self.cap_settings_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                    self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                    if self.config["create_topology_plots"]:
                        self.plot_violations()
                else:
                    self.logger.info("No cap banks exist in the system")

            # Do a settings sweep of existing reg control devices (other than sub LTC) after correcting their other
            #  parameters such as ratios etc
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
            self.reg_sweep_viols = {}
            if dss.RegControls.Count() > 0 and len(self.buses_with_violations) > 0:
                self.logger.info("Settings sweep for existing reg control devices (other than sub LTC).")
                self.initial_regctrls_settings = {}
                reg_cnt = 0
                dss.RegControls.First()
                while True:
                    name = dss.RegControls.Name()
                    xfmr = dss.RegControls.Transformer()
                    dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                    xfmr_buses = dss.CktElement.BusNames()
                    xfmr_b1 = xfmr_buses[0].split(".")[0]
                    xfmr_b2 = xfmr_buses[1].split(".")[0]
                    # # Skipping over substation LTC if it exists
                    # for n, d in self.G.in_degree().items():
                    #     if d==0:
                    #         sourcebus = n
                    sourcebus = self.source
                    if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                        dss.Circuit.SetActiveElement("Regcontrol.{}".format(name))
                        # dss.RegControls.Next()
                        if not dss.RegControls.Next() > 0:
                            break
                        continue
                    reg_cnt+=1
                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(name))
                    bus_name = dss.CktElement.BusNames()[0].split(".")[0]
                    dss.Circuit.SetActiveBus(bus_name)
                    phases = dss.CktElement.NumPhases()
                    kV = dss.Bus.kVBase()
                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(name))
                    winding = self.LTC_wdg
                    reg_delay = self.LTC_delay
                    pt_ratio = kV * 1000 / (self.config["nominal_voltage"])
                    try:
                        Vreg = dss.Properties.Value("vreg")
                    except:
                        Vreg = self.config["nominal_voltage"]
                    try:
                        bandwidth = dss.Properties.Value("band")
                    except:
                        bandwidth = 3.0
                    self.initial_regctrls_settings[name] = [Vreg, bandwidth]
                    command_string = "Edit RegControl.{rn} transformer={tn} winding={w} vreg={sp} ptratio={rt} band={b} " \
                                     "enabled=true delay={d} !original".format(
                        rn=name,
                        tn=xfmr,
                        w=winding,
                        sp=Vreg,
                        rt=pt_ratio,
                        b=bandwidth,
                        d=reg_delay
                    )
                    dss.run_command(command_string)
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    # add this to a dss_upgrades.dss file
                    self.write_dss_file(command_string)
                    if not dss.RegControls.Next() > 0:
                        break
                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                if reg_cnt > 1:
                    self.reg_sweep_viols["original"] = self.severity_indices[2]
                if len(self.buses_with_violations) > 0:
                    self.reg_controls_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                    self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                    if self.config["create_topology_plots"]:
                        self.plot_violations()

            # Writing out the results before adding new devices
            self.logger.info("Write upgrades to dss file, before adding new devices.")
            self.write_upgrades_to_file()
            # TODO: decide whether postprocess should be done once before going to next stage of adding objects
            # postprocess_voltage_upgrades(
            #     {
            #         "outputs": self.config["Outputs"],
            #         "feederhead_name": self.feeder_head_name,
            #         "feederhead_basekV": self.feeder_head_basekv
            #     },
            #     self.logger,
            # )

            # New devices might be added after this
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
            self.cluster_optimal_reg_nodes = {}
            self.cluster_optimal_reg_nodes["pre_reg"] = [self.severity_indices[2]]
            self.sub_LTC_added_flag = 0

            # Use this block for adding a substation LTC, correcting its settings and running a sub LTC settings sweep -
            # if LTC exists first try to correct its non set point simulation settings - if this does not correct everything
            #  correct its set points through a sweep - if LTC does not exist add one including a xfmr if required - then
            #  do a settings sweep if required
            # self.add_ctrls_flag = 0
            # TODO: If adding a substation LTC increases violations even after the control sweep then before then remove it
            # TODO: - this might however interfere with voltage regulator logic so may be let it be there
            if self.config["use_ltc_placement"]:
                self.logger.info("Add/Correct/Sweep settings for Substation LTC.")
                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                if len(self.buses_with_violations) > 0:
                    if self.config["create_topology_plots"]:
                        self.plot_violations()
                    # Add substation LTC if not available (may require addition of a new substation xfmr as well)
                    # if available correct its settings
                    self.subLTC_sweep_viols = {}
                    self.LTC_exists_flag = 0
                    if dss.RegControls.Count() > 0 and len(self.buses_with_violations) > 0:
                        self.initial_subLTC_settings = {}
                        dss.RegControls.First()
                        while True:
                            name = dss.RegControls.Name()
                            xfmr = dss.RegControls.Transformer()
                            dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                            xfmr_buses = dss.CktElement.BusNames()
                            xfmr_b1 = xfmr_buses[0].split(".")[0]
                            xfmr_b2 = xfmr_buses[1].split(".")[0]
                            # for n, d in self.G.in_degree().items():
                            #     if d==0:
                            #         sourcebus = n
                            sourcebus = self.source
                            # Skipping over all reg controls other than sub LTC
                            if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                                self.LTC_exists_flag = 1
                                dss.Circuit.SetActiveElement("Regcontrol.{}".format(name))
                                bus_name = dss.CktElement.BusNames()[0].split(".")[0]
                                dss.Circuit.SetActiveBus(bus_name)
                                phases = dss.CktElement.NumPhases()
                                kV = dss.Bus.kVBase()
                                winding = self.LTC_wdg
                                reg_delay = self.LTC_delay
                                pt_ratio = kV * 1000 / (self.config["nominal_voltage"])
                                try:
                                    Vreg = dss.Properties.Value("vreg")
                                except:
                                    Vreg = self.config["nominal_voltage"]
                                try:
                                    bandwidth = dss.Properties.Value("band")
                                except:
                                    bandwidth = 3.0
                                self.initial_subLTC_settings[name] = [Vreg, bandwidth]
                                command_string = "Edit RegControl.{rn} transformer={tn} winding={w} vreg={sp} ptratio={rt} band={b} " \
                                                 "enabled=true delay={d} !original".format(
                                    rn=name,
                                    tn=xfmr,
                                    w=winding,
                                    sp=Vreg,
                                    rt=pt_ratio,
                                    b=bandwidth,
                                    d=reg_delay
                                )
                                dss.run_command(command_string)
                                self.dssSolver.Solve()
                                self._simulation.RunStep(self._step)
                                # add this to a dss_upgrades.dss file
                                self.write_dss_file(command_string)
                                dss.Circuit.SetActiveElement("Regcontrol.{}".format(name))
                            if not dss.RegControls.Next() > 0:
                                break
                        if self.LTC_exists_flag == 1:
                            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                    lower_limit=self.lower_limit)
                            self.subLTC_sweep_viols["original"] = self.severity_indices[2]
                            if len(self.buses_with_violations) > 0:
                                self.LTC_controls_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)

                                self.create_final_comparison(project_path=self.config["project_dss_files_path"],
                                                             thermal_dss_file=thermal_dss_file)
                                pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                                    lower_limit=self.lower_limit,
                                                                                    raise_exception=False)  # TODO
                                # TODO: pass flag to be used: if pass_flag is false, just go to create comparison file
                                if self.config["create_topology_plots"]:
                                    self.plot_violations()
                        elif self.LTC_exists_flag == 0:
                            self.add_substation_LTC()
                            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                    lower_limit=self.lower_limit)
                            self.cluster_optimal_reg_nodes["sub_LTC"] = [self.severity_indices[2]]
                            self.sub_LTC_added_flag = 1
                            if len(self.buses_with_violations) > 0:
                                self.LTC_controls_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                                pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                                    lower_limit=self.lower_limit,
                                                                                    raise_exception=False)
                                # TODO: this pass flag is to be used:
                                #  if pass_flag is false, then just go to create comparison file
                                if self.config["create_topology_plots"]:
                                    self.plot_violations()
                    elif dss.RegControls.Count() == 0 and len(self.buses_with_violations) > 0:
                        self.add_substation_LTC()
                        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                lower_limit=self.lower_limit)
                        self.cluster_optimal_reg_nodes["sub_LTC"] = [self.severity_indices[2]]
                        self.sub_LTC_added_flag = 1
                        if len(self.buses_with_violations) > 0:
                            self.LTC_controls_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
                            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                    lower_limit=self.lower_limit)
                            if self.config["create_topology_plots"]:
                                self.plot_violations()

            # Correct regulator settings if regs are present in the feeder other than the sub station LTC
            # TODO: Remove regs of last iteration
            pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                lower_limit=self.lower_limit,
                                                                raise_exception=False)  # TODO
            # TODO: pass flag to be used: if pass_flag is false, then just go to create comparison file

            self.logger.info(f"Total number of buses in circuit: {len(dss.Circuit.AllBusNames())}")
            # if number of buses with violations is very high, the loop for adding new regulators will take very long
            # so disable this block - current condition is if number of violations > 250
            if len(self.buses_with_violations) >= min((100 * len(self.initial_buses_with_violations)), 500,
                                                     len(dss.Circuit.AllBusNames())
                                                     ):
                self.logger.info(f"At this point, number of buses with violations is {len(self.buses_with_violations)},"
                                 f" but initial number of buses with violations is "
                                 f"{len(self.initial_buses_with_violations)}")
                self.logger.info("So disable option for addition of new regulators")
                self.place_new_regulators = False

            # if option to place new regulators is disabled
            if (len(self.buses_with_violations) > 1) and (not self.place_new_regulators):
                self.logger.info("Ignoring block for adding new regulators")
                # determining key with minimum objective func. at various levels
                # (at this point includes pre-reg, sub-LTC)
                min_cluster = ''
                min_severity = 1000000000
                # TODO - below logic for min_severity was used previously - however, error cases were encountered
                #  for some feeders due to min_severity being not large enough
                # min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * self.upper_limit
                for key, vals in self.cluster_optimal_reg_nodes.items():
                    if vals[0] < min_severity:
                        min_severity = vals[0]
                        min_cluster = key
                self.logger.info(f"Checking objective function to determine best possible upgrades.\n"
                                 f"At stages: 1) Before addition of new devices. "
                                 f"2) With Substation LTC.")
                self.compare_objective_function(min_cluster)

            # if option to place new regulators is enabled
            elif (len(self.buses_with_violations) > 1) and (self.place_new_regulators):
                if self.config["create_topology_plots"]:
                    self.plot_violations()
                # for n, d in self.G.in_degree().items():
                #     if d == 0:
                #         self.source = n
                # Place additional regulators if required
                self.logger.info("Sweep by placing additional regulators")
                self.logger.info(f"Number of buses with violations:{len(self.buses_with_violations)}")
                self.max_regs = int(min(self.config["max_regulators"], len(self.buses_with_violations)))
                self.get_shortest_path()
                self.get_full_distance_dict()
                self.cluster_square_array()
                min_severity = 1000000000
                # TODO - below logic for min_severity was used previously - however, error cases were encountered
                #  for some feeders due to min_severity being not large enough
                # min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * self.upper_limit

                #  determining key with minimum objective func. at various levels
                # (at this point includes pre-reg, sub-LTC, and all newly added regulators)
                min_cluster = ''
                for key, vals in self.cluster_optimal_reg_nodes.items():
                    if vals[0] < min_severity:
                        min_severity = vals[0]
                        min_cluster = key
                # Logic is if violations were less before addition of any device, revert back to that condition by removing
                #  added LTC and not adding best determined in-line regs, else if LTC was best - pass and do not add new
                #  in-line regs, or if some better LTC placemenr was determined apply that
                self.logger.info(f"Checking objective function to determine best possible upgrades.\n"
                                 f"At stages: 1) Before addition of new devices. "
                                 f"2) With Substation LTC. 3) With newly added regulators")
                self.compare_objective_function(min_cluster)

                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                        lower_limit=self.lower_limit)
                self.logger.info("Compare objective with best and applied settings, %s, %s", self.cluster_optimal_reg_nodes[min_cluster][0],
                      self.severity_indices[2])
                self.logger.info("Additional regctrl  devices: %s", min_cluster)
                self.logger.info("cluster_optimal_reg_nodes=%s", self.cluster_optimal_reg_nodes)

        self.end_t = time.time()  # used to determine time taken for run

        self.create_final_comparison(project_path=self.config["project_dss_files_path"], thermal_dss_file=thermal_dss_file)

        # go to voltage upgrades post processing script
        postprocess_voltage_upgrades(
            {
                "outputs": self.config["Outputs"],
                "feederhead_name": self.feeder_head_name,
                "feederhead_basekV": self.feeder_head_basekv,
                "orig_ckt_info": self.orig_ckt_info,
                "new_reg_controls": self.new_reg_controls,
                "orig_reg_controls": self.orig_reg_controls,
                "new_capacitors": self.new_capacitors,
                "orig_capacitors": self.orig_capacitors,
                "new_capcontrols": self.new_capcontrols,
                "orig_capcontrols": self.orig_capcontrols,
                "orig_xfmr_info": self.orig_xfmr_info,
                "new_xfmr_info": self.new_xfmr_info,
                "new_ckt_info": self.new_ckt_info,
            },
            self.logger,
        )
        self.has_converged = dss.Solution.Converged()
        self.error = dss.Solution.Convergence()  # TODO This is fake for now, find how to get this from Opendssdirect

    @staticmethod
    def _get_required_input_fields():
        return AutomatedVoltageUpgrade.REQUIRED_INPUT_FIELDS

    def create_final_comparison(self, project_path=None, thermal_dss_file=None):
        self.logger.debug("Writing upgrades to DSS file")
        self.write_upgrades_to_file()

        self.logger.info("Checking impact of redirected upgrades file")
        dss.run_command("Clear")
        base_dss = os.path.join(project_path, self.Settings.project.dss_file)
        check_redirect(base_dss)
        check_redirect(thermal_dss_file)
        upgrades_file = os.path.join(self.config["Outputs"], "voltage_upgrades.dss")
        check_redirect(upgrades_file)
        self.dssSolver.Solve()
        self._simulation.RunStep(self._step)

        self.new_reg_controls = {x["name"]: x for x in iter_elements(dss.RegControls, get_reg_control_info)}
        self.new_capacitors = {x["name"]: x for x in iter_elements(dss.Capacitors, get_capacitor_info)}
        self.new_capcontrols = {x["name"]: x for x in iter_elements(dss.CapControls, get_cap_controls_info)}
        self.new_xfmr_info = dss.Transformers.AllNames()
        self.new_ckt_info = get_ckt_info()

        self.create_result_comparison_voltages(comparison_stage='After Upgrades')

        self.feeder_parameters["Simulation time (seconds)"] = self.end_t-self.start_t
        self.feeder_parameters["Upgrade status"] = self.upgrade_status
        self.feeder_parameters["feederhead_name"] = self.feeder_head_name
        self.feeder_parameters["feederhead_basekV"] = self.feeder_head_basekv

        self.write_to_json(self.feeder_parameters, "Voltage_violations_comparison")
        return

    # this function create comparison file
    def create_result_comparison_voltages(self, comparison_stage=''):
        # If initial and final limits are different,
        # also doing with final limits to get comparison between initial and final violation numbers
        if (self.config["final_voltage_upper_limit"] != self.config["initial_voltage_upper_limit"]) or \
                (self.config["final_voltage_lower_limit"] != self.config["initial_voltage_lower_limit"]):
            self.logger.info(f"Initial and Final voltage limits are not the same. "
                             f"\ninitial_voltage_lower_limit: {self.config['initial_voltage_lower_limit']}, "
                             f"initial_voltage_upper_limit: {self.config['initial_voltage_upper_limit']} "
                             f"\nfinal_voltage_lower_limit: {self.config['final_voltage_lower_limit']}, "
                             f"final_voltage_upper_limit: {self.config['final_voltage_upper_limit']}")

            self.upper_limit = self.config["final_voltage_upper_limit"]
            self.lower_limit = self.config["final_voltage_lower_limit"]
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)

            self.logger.info(f"Based on Lower limit: {self.lower_limit}, Upper limit: {self.upper_limit}")
            self.logger.info("{} number of buses with violations are: {}".format(comparison_stage,
                                                                                 len(self.buses_with_violations)))
            self.logger.info("{} objective function value: {}".format(comparison_stage, self.severity_indices[2]))

            self.feeder_parameters["{}_violations_2".format(comparison_stage)] = {
                "Voltage upper threshold": self.upper_limit,
                "Voltage lower threshold": self.lower_limit,
                "Number of buses with violations": len(self.buses_with_violations),
                "Number of buses with overvoltage violations": len(self.buses_with_overvoltage_violations),
                "Number of buses with undervoltage violations": len(self.buses_with_undervoltage_violations),
                "Buses at all tps with violations": self.severity_indices[0],
                "Severity of bus violations": self.severity_indices[1],
                "Objective function value": self.severity_indices[2],
                "Maximum voltage observed": self.max_V_viol,
                "Minimum voltage observed": self.min_V_viol
            }

        # change violation checking thresholds to initial limit - to ensure uniform comparison betn initial & final
        self.upper_limit = self.config["initial_voltage_upper_limit"]
        self.lower_limit = self.config["initial_voltage_lower_limit"]

        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                lower_limit=self.lower_limit)
        if self.config["create_topology_plots"]:
            self.plot_violations()
        self.logger.info("{} maximum voltage observed on any node: {} {}".format(comparison_stage, self.max_V_viol,
                                                                                 self.busvmax))
        self.logger.info("{} minimum voltage observed on any node: {}".format(comparison_stage, self.min_V_viol))
        self.logger.info(f"Based on Lower limit: {self.lower_limit}, Upper limit: {self.upper_limit}")
        self.logger.info("{} number of buses with violations are: {}".format(comparison_stage,
                                                                             len(self.buses_with_violations)))
        self.logger.info("{} objective function value: {}".format(comparison_stage, self.severity_indices[2]))

        self.feeder_parameters["{}_violations".format(comparison_stage)] = {
            "Voltage upper threshold": self.upper_limit,
            "Voltage lower threshold": self.lower_limit,
            "Number of buses with violations": len(self.buses_with_violations),
            "Number of buses with overvoltage violations": len(self.buses_with_overvoltage_violations),
            "Number of buses with undervoltage violations": len(self.buses_with_undervoltage_violations),
            "Buses at all tps with violations": self.severity_indices[0],
            "Severity of bus violations": self.severity_indices[1],
            "Objective function value": self.severity_indices[2],
            "Maximum voltage observed": self.max_V_viol,
            "Minimum voltage observed": self.min_V_viol
        }
        return

    def get_load_pv_mults_individual_object(self):
        self.orig_loads = {}
        self.orig_pvs = {}
        self.dssSolver.Solve()
        self._simulation.RunStep(self._step)
        if dss.Loads.Count() > 0:
            dss.Loads.First()
            while True:
                load_name = dss.Loads.Name().split(".")[0].lower()
                kW = dss.Loads.kW()
                self.orig_loads[load_name] = [kW]
                if not dss.Loads.Next() > 0:
                    break
            for key, dss_paths in self.other_load_dss_files.items():
                self.read_load_files_individual_object(key, dss_paths)

        if dss.PVsystems.Count() > 0:
            dss.PVsystems.First()
            while True:
                pv_name = dss.PVsystems.Name().split(".")[0].lower()
                pmpp = float(dss.Properties.Value("irradiance"))
                self.orig_pvs[pv_name] = [pmpp]
                if not dss.PVsystems.Next() > 0:
                    break
            for key, dss_paths in self.other_pv_dss_files.items():
                self.read_pv_files_individual_object(key, dss_paths)

    def read_load_files_individual_object(self,key_paths,dss_path):
        # Add all load kW values
        temp_dict = {}
        for path_f in dss_path:
            with open(path_f, "r") as datafile:
                for line in datafile:
                    if line.lower().startswith("new load."):
                        for params in line.split():
                            if params.lower().startswith("load."):
                                ld_name = params.lower().split("load.")[1]
                            if params.lower().startswith("kw"):
                                ld_kw = float(params.lower().split("=")[1])
                        temp_dict[ld_name] = ld_kw
        for key,vals in self.orig_loads.items():
            if key in temp_dict:
                self.orig_loads[key].append(temp_dict[key])
            elif key not in temp_dict:
                self.orig_loads[key].append(self.orig_loads[key][0])

    def read_pv_files_individual_object(self, key_paths, dss_path):
        # Add all PV pmpp values
        temp_dict = {}
        for path_f in self.other_pv_dss_files[key_paths]:
            with open(path_f, "r") as datafile:
                for line in datafile:
                    if line.lower().startswith("new pvsystem."):
                        for params in line.split():
                            if params.lower().startswith("pvsystem."):
                                pv_name = params.lower().split("pvsystem.")[1]
                            if params.lower().startswith("irradiance"):
                                pv_pmpp = float(params.lower().split("=")[1])
                        temp_dict[pv_name] = pv_pmpp
        for key, vals in self.orig_pvs.items():
            if key in temp_dict:
                self.orig_pvs[key].append(temp_dict[key])
            elif key not in temp_dict:
                self.orig_pvs[key].append(self.orig_pvs[key][0])

    def get_load_mults(self):
        self.orig_loads = {}
        self.dssSolver.Solve()
        self._simulation.RunStep(self._step)
        dss.Loads.First()
        while True:
            load_name = dss.Loads.Name().split(".")[0].lower()
            kW = dss.Loads.kW()
            self.orig_loads[load_name] = [kW]
            if not dss.Loads.Next()>0:
                break
        for dss_path in self.other_load_dss_files:
            self.read_load_files(dss_path)
        self.get_min_max_load_mult()

    def read_load_files(self, dss_path):
        with open(dss_path, "r") as datafile:
            for line in datafile:
                if line.lower().startswith("new load."):
                    for params in line.split():
                        if params.lower().startswith("load."):
                            ld_name = params.lower().split("load.")[1]
                        if params.lower().startswith("kw"):
                            ld_kw = float(params.lower().split("=")[1])
                    if ld_name in self.orig_loads:
                        self.orig_loads[ld_name].append(ld_kw)

    def get_min_max_load_mult(self):
        self.min_max_load_kw = {}
        for key,vals in self.orig_loads.items():
            self.min_max_load_kw[key] = [min(vals),max(vals)]

    def compare_objective_function(self, min_cluster):
        # Logic is if violations were less before addition of any device, revert back to that condition by removing
        #  added LTC and not adding best determined in-line regs, else if LTC was best - pass and do not add new
        #  in-line regs, or if some better LTC placement was determined apply that
        if min_cluster == "pre_reg":
            self.logger.info("Violations were less before addition of any new regulator or substation LTC.")
            self.logger.info("Remove substation LTC and best in-line reg.")
            # This will remove LTC controller, but if initially there was no substation transformer
            # (highly unlikely) the added transformer will still be there
            if self.sub_LTC_added_flag == 1:
                if self.subxfmr == '':
                    LTC_reg_node = self.source
                elif self.subxfmr != '':
                    LTC_reg_node = self.sub_LTC_bus
                LTC_name = "New_regctrl_" + LTC_reg_node
                command_string = "Edit RegControl.{ltc_nm} enabled=False".format(
                    ltc_nm=LTC_name
                )
                dss.run_command(command_string)
                self.write_dss_file(command_string)
            else:
                pass
        elif min_cluster == "sub_LTC":
            self.logger.info("Setting with substation LTC is best.")
            pass
        else:
            self.logger.info("Setting with new regulator placement is best.")
            for reg_nodes in self.cluster_optimal_reg_nodes[min_cluster][2]:
                self.write_flag = 1
                self.add_new_xfmr(reg_nodes)
                self.add_new_regctrl(reg_nodes)
                rn_name = "New_regctrl_" + reg_nodes
                command_string = "Edit RegControl.{rn} vreg={vsp} band={b}".format(
                    rn=rn_name,
                    vsp=self.cluster_optimal_reg_nodes[min_cluster][1][0],
                    b=self.cluster_optimal_reg_nodes[min_cluster][1][1]
                )
                dss.run_command(command_string)
                dss.run_command("CalcVoltageBases")
                self.write_dss_file(command_string)
            # After all additional devices have been placed perform the cap bank settings sweep again-
            # only if new devices were accepted

            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)
            if dss.CapControls.Count() > 0 and len(self.buses_with_violations) > 0:
                self.logger.info("Violations still exist -> Sweep capacitor settings again, "
                                 "after new devices are placed.")
                self.cap_settings_sweep(upper_limit=self.upper_limit,
                                        lower_limit=self.lower_limit)
                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                        lower_limit=self.lower_limit)
                if self.config["create_topology_plots"]:
                    self.plot_violations()
            self.write_dss_file("CalcVoltageBases")

    def get_existing_controller_info(self):
        self.cap_control_info = {}
        self.reg_control_info = {}

        cap_bank_list = []
        if dss.CapControls.Count() > 0:
            dss.CapControls.First()
            while True:
                cap_ctrl = dss.CapControls.Name().lower()
                cap_name = dss.CapControls.Capacitor().lower()
                cap_bank_list.append(cap_name)
                ctrl_type = dss.Properties.Value("type")
                on_setting = dss.CapControls.ONSetting()
                off_setting = dss.CapControls.OFFSetting()
                dss.Capacitors.Name(cap_name)
                if not cap_name.lower() == dss.Capacitors.Name().lower():
                    raise InvalidParameter("Incorrect Active Element")
                cap_size = dss.Capacitors.kvar()
                cap_kv = dss.Capacitors.kV()
                self.cap_control_info[cap_ctrl] = {
                    "cap_name": cap_name,
                    "cap kVAR": cap_size,
                    "cap_kv": cap_kv,
                    "Control type": ctrl_type,
                    "ON": on_setting,
                    "OFF": off_setting
                }
                dss.Circuit.SetActiveElement("CapControl.{}".format(cap_ctrl))
                if not dss.CapControls.Next() > 0:
                    break

        if dss.RegControls.Count() > 0:
            dss.RegControls.First()
            while True:
                reg_ctrl = dss.RegControls.Name().lower()
                dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_ctrl)) ##
                reg_vsp = dss.Properties.Value("vreg")
                reg_band = dss.Properties.Value("band")
                xfmr_name = dss.RegControls.Transformer().lower()
                dss.Transformers.Name(xfmr_name)
                if not xfmr_name.lower() == dss.Transformers.Name().lower():
                    raise InvalidParameter("Incorrect Active Element")
                xfmr_buses = dss.CktElement.BusNames()
                # bus_names = []
                # for buses in xfmr_buses:
                #     bus_names.append(buses.split(".")[0].lower())
                # if self.source.lower() in bus_names:
                #     self.sub_xfmr_cap = 1
                xfmr_size = dss.Transformers.kVA()
                xfmr_kv = dss.Transformers.kV()
                self.reg_control_info[reg_ctrl] = {
                    "reg_vsp": reg_vsp,
                    "reg_band": reg_band,
                    "xfmr_name": xfmr_name,
                    "xfmr kVA": xfmr_size,
                    "xfmr_kv": xfmr_kv
                }
                dss.Circuit.SetActiveElement("RegControl.{}".format(reg_ctrl))
                if not dss.RegControls.Next() > 0:
                    break

        # if self.sub_xfmr_cap==0:
        dss.Transformers.First()
        while True:
            bus_names = dss.CktElement.BusNames()
            bus_names_only = []
            for buses in bus_names:
                bus_names_only.append(buses.split(".")[0].lower())
            if self.source.lower() in bus_names_only:
                sub_xfmr = dss.Transformers.Name()
                self.reg_control_info["orig_substation_xfmr"] = {
                    "xfmr_name": sub_xfmr,
                    "xfmr kVA": dss.Transformers.kVA(),
                    "xfmr_kv": dss.Transformers.kV(),
                    "bus_names": bus_names_only
                }
            if not dss.Transformers.Next() > 0:
                break

        if dss.Capacitors.Count() > 0:
            dss.Capacitors.First()
            while True:
                cap_name = dss.Capacitors.Name().lower()
                cap_size = dss.Capacitors.kvar()
                cap_kv = dss.Capacitors.kV()
                ctrl_type = "NA"
                if cap_name not in cap_bank_list:
                    self.cap_control_info["capbank_noctrl_{}".format(cap_name)] = {
                        "cap_name": cap_name,
                        "cap kVAR": cap_size,
                        "cap_kv": cap_kv,
                        "Control type": ctrl_type
                    }
                if not dss.Capacitors.Next() > 0:
                    break

        self.write_to_json(self.cap_control_info, "Initial_capacitors")
        self.write_to_json(self.reg_control_info, "Initial_regulators")

    def write_to_json(self, dict, file_name):
        with open(os.path.join(self.config["Outputs"], "{}.json".format(file_name)), "w") as fp:
            json.dump(dict, fp, indent=4)

    def generate_nx_representation(self):
        self.all_bus_names = dss.Circuit.AllBusNames()
        self.G = nx.DiGraph()
        self.generate_nodes()
        self.generate_edges()
        self.pos_dict = nx.get_node_attributes(self.G, 'pos')
        if self.config["create_topology_plots"]:
            self.correct_node_coords()

    def correct_node_coords(self):
        # If node doesn't have node attributes, attach parent or child node's attributes
        new_temp_graph = self.G
        temp_graph = new_temp_graph.to_undirected()
        # for n, d in self.G.in_degree().items():
        #     if d == 0:
        #         self.source = n
        for key, vals in self.pos_dict.items():
            if vals[0] == 0.0 and vals[1] == 0.0:
                new_x = 0
                new_y = 0
                pred_buses = nx.shortest_path(temp_graph, source=key, target=self.source)
                if len(pred_buses) > 0:
                    for pred_bus in pred_buses:
                        if pred_bus == key:
                            continue
                        if self.pos_dict[pred_bus][0] != 0.0 and self.pos_dict[pred_bus][1] != 0.0:
                            new_x = self.pos_dict[pred_bus][0]
                            new_y = self.pos_dict[pred_bus][1]
                            self.G.node[key]["pos"] = [new_x, new_y]
                            break
                if new_x == 0 and new_y == 0:
                    # Since either predecessor nodes were not available or they did not have
                    # non-zero coordinates, try successor nodes
                    # Get a leaf node
                    for x in self.G.nodes():
                        if self.G.out_degree(x) == 0 and self.G.in_degree(x) == 1:
                            leaf_node = x
                            break
                    succ_buses = nx.shortest_path(temp_graph, source=key, target=leaf_node)
                    if len(succ_buses) > 0:
                        for pred_bus in succ_buses:
                            if pred_bus == key:
                                continue
                            if self.pos_dict[pred_bus][0] != 0.0 and self.pos_dict[pred_bus][1] != 0.0:
                                new_x = self.pos_dict[pred_bus][0]
                                new_y = self.pos_dict[pred_bus][1]
                                self.G.node[key]["pos"] = [new_x, new_y]
                                break
        # Update pos dict with new coordinates
        self.pos_dict = nx.get_node_attributes(self.G, 'pos')

    def generate_nodes(self):
        self.nodes_list = []
        for b in self.all_bus_names:
            dss.Circuit.SetActiveBus(b)
            name = b.lower()
            position = []
            position.append(dss.Bus.X())
            position.append(dss.Bus.Y())
            self.G.add_node(name, pos=position)
            self.nodes_list.append(b)

    def generate_edges(self):
        '''
        All lines, switches, reclosers etc are modeled as lines, so calling lines takes care of all of them.
        However we also need to loop over transformers as they form the edge between primary and secondary nodes
        :return:
        '''
        dss.Lines.First()
        while True:
            from_bus = dss.Lines.Bus1().split('.')[0].lower()
            to_bus = dss.Lines.Bus2().split('.')[0].lower()
            phases = dss.Lines.Phases()
            length = dss.Lines.Length()
            name = dss.Lines.Name()
            if dss.Lines.Units() == 1:
                length = length * 1609.34
            elif dss.Lines.Units() == 2:
                length = length * 304.8
            elif dss.Lines.Units() == 3:
                length = length * 1000
            elif dss.Lines.Units() == 4:
                length = length
            elif dss.Lines.Units() == 5:
                length = length * 0.3048
            elif dss.Lines.Units() == 6:
                length = length * 0.0254
            elif dss.Lines.Units() == 7:
                length = length * 0.01
            self.G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
            if not dss.Lines.Next() > 0:
                break

        dss.Transformers.First()
        while True:
            bus_names = dss.CktElement.BusNames()
            from_bus = bus_names[0].split('.')[0].lower()
            to_bus = bus_names[1].split('.')[0].lower()
            phases = dss.CktElement.NumPhases()
            length = 0.0
            name = dss.Transformers.Name()
            self.G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
            if not dss.Transformers.Next() > 0:
                break

    def plot_feeder(self):
        plt.figure(figsize=(7, 7))
        ec = nx.draw_networkx_edges(self.G, pos=self.pos_dict, alpha=1.0, width=0.3)
        ldn = nx.draw_networkx_nodes(self.G, pos=self.pos_dict, nodelist=self.nodes_list, node_size=8,
                                     node_color='k', alpha=1)
        ld = nx.draw_networkx_nodes(self.G, pos=self.pos_dict, nodelist=self.nodes_list, node_size=6,
                                    node_color='yellow', alpha=0.7)

        nx.draw_networkx_labels(self.G, pos=self.pos_dict, node_size=1, font_size=15)
        plt.title("Feeder with all customers having DPV systems")
        plt.axis("off")
        plt.show()

    # (not used) check voltage violations when we have multipliers for individual load and PV
    def check_voltage_violations_multi_tps_individual_object(self, upper_limit, lower_limit):
        # TODO: This objective currently gives more weightage if same node has violations at more than 1 time point
        num_nodes_counter = 0
        severity_counter = 0
        self.max_V_viol = 0
        self.min_V_viol = 2
        self.buses_with_violations = []
        self.buses_with_violations_pos = {}
        self.nodal_violations_dict = {}
        # If multiple load files are being used, the 'tps_to_test property is not used, else if a single load file is
        # used use the 'tps to test' input
        for tp_cnt in range(len(self.other_load_dss_files)):
            # Apply correct pmpp values to all PV systems
            if dss.PVsystems.Count() > 0:
                dss.PVsystems.First()
                while True:
                    pv_name = dss.PVsystems.Name().split(".")[0].lower()
                    if pv_name not in self.orig_pvs:
                        raise Exception("PV system not found, quitting...")
                    new_pmpp = self.orig_pvs[pv_name][tp_cnt]
                    dss.run_command(f"Edit PVsystem.{pv_name} irradiance={new_pmpp}")
                    if not dss.PVsystems.Next()>0:
                        break
            # Apply correct kW value to all loads
            if dss.Loads.Count() > 0:
                dss.Loads.First()
                while True:
                    load_name = dss.Loads.Name().split(".")[0].lower()
                    if load_name not in self.orig_loads:
                        raise Exception("Load not found, quitting...")
                    new_kw = self.orig_loads[load_name][tp_cnt]
                    dss.Loads.kW(new_kw)
                    if not dss.Loads.Next() > 0:
                        break
            self.dssSolver.Solve()
            self._simulation.RunStep(self._step)
            if not dss.Solution.Converged():
                self.logger.info("Write upgrades till this step in debug_upgrades.dss")
                self.write_upgrades_to_file(output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
                raise OpenDssConvergenceError("OpenDSS solution did not converge")
            for b in self.all_bus_names:
                dss.Circuit.SetActiveBus(b)
                bus_v = dss.Bus.puVmagAngle()[::2]
                # Select that bus voltage of the three phases which is outside bounds the most,
                #  else if everything is within bounds use nominal pu voltage.
                maxv_dev = 0
                minv_dev = 0
                if max(bus_v) > self.max_V_viol:
                    self.max_V_viol = max(bus_v)
                    self.busvmax = b
                if min(bus_v) < self.min_V_viol:
                    self.min_V_viol = min(bus_v)
                if max(bus_v) > upper_limit:
                    maxv = max(bus_v)
                    maxv_dev = maxv - upper_limit
                if min(bus_v) < lower_limit:
                    minv = min(bus_v)
                    minv_dev = upper_limit - minv
                if maxv_dev > minv_dev:
                    v_used = maxv
                    num_nodes_counter += 1
                    severity_counter += maxv_dev
                    if b.lower() not in self.buses_with_violations:
                        self.buses_with_violations.append(b.lower())
                        self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                elif minv_dev > maxv_dev:
                    v_used = minv
                    num_nodes_counter += 1
                    severity_counter += minv_dev
                    if b.lower() not in self.buses_with_violations:
                        self.buses_with_violations.append(b.lower())
                        self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                else:
                    v_used = self.config["nominal_pu_voltage"]
                if b not in self.nodal_violations_dict:
                    self.nodal_violations_dict[b.lower()] = [v_used]
                elif b in self.nodal_violations_dict:
                    self.nodal_violations_dict[b.lower()].append(v_used)
        self.severity_indices = [num_nodes_counter, severity_counter, num_nodes_counter * severity_counter]
        return

    # this function checks for voltage violations based on upper and lower limit passed
    def check_voltage_violations_multi_tps(self, upper_limit, lower_limit, raise_exception=True):
        # TODO: This objective currently gives more weightage if same node has violations at more than 1 time point
        num_nodes_counter = 0
        severity_counter = 0
        self.max_V_viol = 0
        self.min_V_viol = 2
        self.buses_with_violations = []
        self.buses_with_undervoltage_violations = []
        self.buses_with_overvoltage_violations = []
        self.buses_with_violations_pos = {}
        self.nodal_violations_dict = {}
        # If multiple load files are being used, the 'tps_to_test property is not used, else if a single load file is
        # used use the 'tps to test' input
        if len(self.other_load_dss_files)>0:
            for tp_cnt in range(len(self.config["tps_to_test"])):
                # First two tps are for disabled PV case
                if tp_cnt == 0 or tp_cnt == 1:
                    dss.run_command("BatchEdit PVSystem..* Enabled=False")
                    dss.Loads.First()
                    while True:
                        load_name = dss.Loads.Name().split(".")[0].lower()
                        if load_name not in self.min_max_load_kw:
                            raise Exception("Load not found, quitting...")
                        new_kw = self.min_max_load_kw[load_name][tp_cnt]
                        dss.Loads.kW(new_kw)
                        if not dss.Loads.Next()>0:
                            break
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    if not dss.Solution.Converged():
                        self.logger.info("Write upgrades before Convergence Error in debug_upgrades.dss")
                        self.write_upgrades_to_file(
                            output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
                        if raise_exception:
                            raise OpenDssConvergenceError("OpenDSS solution did not converge")
                        else:
                            return False
                if tp_cnt == 2 or tp_cnt == 3:
                    dss.run_command("BatchEdit PVSystem..* Enabled=True")
                    dss.Loads.First()
                    while True:
                        load_name = dss.Loads.Name().split(".")[0].lower()
                        if load_name not in self.min_max_load_kw:
                            raise Exception("Load not found, quitting...")
                        new_kw = self.min_max_load_kw[load_name][tp_cnt-2]
                        dss.Loads.kW(new_kw)
                        if not dss.Loads.Next() > 0:
                            break
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    if not dss.Solution.Converged():
                        self.logger.info("Write upgrades before Convergence Error in debug_upgrades.dss")
                        self.write_upgrades_to_file(
                            output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
                        if raise_exception:
                            raise OpenDssConvergenceError("OpenDSS solution did not converge")
                        else:
                            return False
                for b in self.all_bus_names:
                    dss.Circuit.SetActiveBus(b)
                    bus_v = dss.Bus.puVmagAngle()[::2]
                    # Select that bus voltage of the three phases which is outside bounds the most,
                    #  else if everything is within bounds use nominal pu voltage.
                    maxv_dev = 0
                    minv_dev = 0
                    if max(bus_v) > self.max_V_viol:
                        self.max_V_viol = max(bus_v)
                        self.busvmax = b
                    if min(bus_v) < self.min_V_viol:
                        self.min_V_viol = min(bus_v)
                    if max(bus_v) > upper_limit:
                        maxv = max(bus_v)
                        maxv_dev = maxv - upper_limit
                        if b.lower() not in self.buses_with_overvoltage_violations:
                            self.buses_with_overvoltage_violations.append(b.lower())
                    if min(bus_v) < lower_limit:
                        minv = min(bus_v)
                        minv_dev = upper_limit - minv
                    if maxv_dev > minv_dev:
                        v_used = maxv
                        num_nodes_counter += 1
                        severity_counter += maxv_dev
                        if b.lower() not in self.buses_with_violations:
                            self.buses_with_violations.append(b.lower())
                            self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                        if b.lower() not in self.buses_with_overvoltage_violations:
                            self.buses_with_overvoltage_violations.append(b.lower())
                    elif minv_dev > maxv_dev:
                        v_used = minv
                        num_nodes_counter += 1
                        severity_counter += minv_dev
                        if b.lower() not in self.buses_with_violations:
                            self.buses_with_violations.append(b.lower())
                            self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                        if b.lower() not in self.buses_with_undervoltage_violations:
                            self.buses_with_undervoltage_violations.append(b.lower())
                    else:
                        v_used = self.config["nominal_pu_voltage"]
                    if b not in self.nodal_violations_dict:
                        self.nodal_violations_dict[b.lower()] = [v_used]
                    elif b in self.nodal_violations_dict:
                        self.nodal_violations_dict[b.lower()].append(v_used)

        elif len(self.other_load_dss_files)==0:
            for tp_cnt in range(len(self.config["tps_to_test"])):
                # First two tps are for disabled PV case
                if tp_cnt == 0 or tp_cnt == 1:
                    dss.run_command("BatchEdit PVSystem..* Enabled=False")
                    dss.run_command("set LoadMult = {LM}".format(LM=self.config["tps_to_test"][tp_cnt]))
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    if not dss.Solution.Converged():
                        self.logger.info("Write upgrades before Convergence Error in debug_upgrades.dss")
                        self.write_upgrades_to_file(
                            output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
                        if raise_exception:
                            raise OpenDssConvergenceError("OpenDSS solution did not converge")
                        else:
                            return False
                if tp_cnt == 2 or tp_cnt == 3:
                    dss.run_command("BatchEdit PVSystem..* Enabled=True")
                    dss.run_command("set LoadMult = {LM}".format(LM=self.config["tps_to_test"][tp_cnt]))
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    if not dss.Solution.Converged():
                        self.logger.info("Write upgrades before Convergence Error in debug_upgrades.dss")
                        self.write_upgrades_to_file(
                            output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
                        if raise_exception:
                            raise OpenDssConvergenceError("OpenDSS solution did not converge")
                        else:
                            return False
                for b in self.all_bus_names:
                    dss.Circuit.SetActiveBus(b)
                    bus_v = dss.Bus.puVmagAngle()[::2]
                    # Select that bus voltage of the three phases which is outside bounds the most,
                    #  else if everything is within bounds use nominal pu voltage.
                    maxv_dev = 0
                    minv_dev = 0
                    if max(bus_v) > self.max_V_viol:
                        self.max_V_viol = max(bus_v)
                        self.busvmax = b
                    if min(bus_v) < self.min_V_viol:
                        self.min_V_viol = min(bus_v)
                    if max(bus_v) > upper_limit:
                        maxv = max(bus_v)
                        maxv_dev = maxv - upper_limit
                        if b.lower() not in self.buses_with_overvoltage_violations:
                            self.buses_with_overvoltage_violations.append(b.lower())
                    if min(bus_v) < lower_limit:
                        minv = min(bus_v)
                        minv_dev = upper_limit - minv
                    if maxv_dev > minv_dev:
                        v_used = maxv
                        num_nodes_counter += 1
                        severity_counter += maxv_dev
                        if b.lower() not in self.buses_with_violations:
                            self.buses_with_violations.append(b.lower())
                            self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                        if b.lower() not in self.buses_with_overvoltage_violations:
                            self.buses_with_overvoltage_violations.append(b.lower())
                    elif minv_dev > maxv_dev:
                        v_used = minv
                        num_nodes_counter += 1
                        severity_counter += minv_dev
                        if b.lower() not in self.buses_with_violations:
                            self.buses_with_violations.append(b.lower())
                            self.buses_with_violations_pos[b.lower()] = self.pos_dict[b.lower()]
                        if b.lower() not in self.buses_with_undervoltage_violations:
                            self.buses_with_undervoltage_violations.append(b.lower())
                    else:
                        v_used = self.config["nominal_pu_voltage"]
                    if b not in self.nodal_violations_dict:
                        self.nodal_violations_dict[b.lower()] = [v_used]
                    elif b in self.nodal_violations_dict:
                        self.nodal_violations_dict[b.lower()].append(v_used)
        self.severity_indices = [num_nodes_counter, severity_counter, num_nodes_counter * severity_counter]
        return True

    def plot_violations(self):
        #plt.figure(figsize=(8, 7))
        plt.figure(figsize=(40, 40), dpi=10)
        plt.clf()
        numV = len(self.buses_with_violations)
        plt.title("Number of buses in the feeder with voltage violations: {}".format(numV))
        ec = nx.draw_networkx_edges(self.G, pos=self.pos_dict, alpha=1.0, width=0.3)
        ld = nx.draw_networkx_nodes(self.G, pos=self.pos_dict, nodelist=self.nodes_list, node_size=2, node_color='b')
        # Show buses with violations
        if len(self.buses_with_violations) > 0:
            m = nx.draw_networkx_nodes(self.G, pos=self.buses_with_violations_pos,
                                       nodelist=self.buses_with_violations, node_size=10, node_color='r')
        plt.axis("off")
        plt.savefig(os.path.join(self.config["Outputs"],"Nodal_violations_{}.pdf".format(str(self.plot_violations_counter))))
        self.plot_violations_counter+=1

    def get_capacitor_state(self):
        # TODO: How to figure out whether cap banks are 3 phase, 2 phase or 1 phase. 1 phase caps will have LN voltage
        self.cap_correct_PTratios = {}
        self.cap_initial_settings = {}
        dss.Capacitors.First()
        while True:
            name = dss.Capacitors.Name()
            # Get original cap bank control settings
            if dss.CapControls.Count() > 0:
                dss.CapControls.First()
                while True:
                    cap_name = dss.CapControls.Capacitor()
                    cap_type = dss.Properties.Value("type")
                    if cap_name == name and cap_type.lower().startswith("volt"):
                        self.cap_initial_settings[name] = [dss.CapControls.ONSetting(), dss.CapControls.OFFSetting()]
                    if not dss.CapControls.Next() > 0:
                        break
            dss.Circuit.SetActiveElement("Capacitor." + name)
            cap_bus = dss.CktElement.BusNames()[0].split(".")[0]
            dss.Circuit.SetActiveBus(cap_bus)
            cap_kv = float(dss.Bus.kVBase())
            dss.Circuit.SetActiveElement("Capacitor." + name)
            PT_ratio = (cap_kv * 1000) / (self.config["nominal_voltage"])
            self.cap_correct_PTratios[name] = PT_ratio
            if not dss.Capacitors.Next() > 0:
                break

    def correct_cap_bank_settings(self):
        # TODO: Add a function to sweep through possible capacitor bank settings
        caps_with_control = []
        cap_on_settings_check = {}
        # Correct settings of those cap banks for which cap control object is available
        if dss.CapControls.Count() > 0:
            dss.CapControls.First()
            while True:
                name = dss.CapControls.Name()
                cap_name = dss.CapControls.Capacitor()
                caps_with_control.append(cap_name)
                orig_sett = ''
                if dss.Properties.Value("type").lower() == "voltage":
                    orig_sett = " !original"
                control_command = "Edit CapControl.{cc} PTRatio={pt} Type={tp} ONsetting={o} OFFsetting={of}" \
                                  " PTphase={ph} Delay={d} DelayOFF={dof} DeadTime={dt} enabled=True".format(
                    cc=name,
                    pt=self.cap_correct_PTratios[cap_name],
                    tp=self.cap_control,
                    o=self.capON,
                    of=self.capOFF,
                    ph=self.PTphase,
                    d=self.capONdelay,
                    dof=self.capOFFdelay,
                    dt=self.capdeadtime
                )
                control_command = control_command + orig_sett
                cap_on_settings_check[cap_name] = self.capON
                dss.run_command(control_command)
                self.dssSolver.Solve()
                self._simulation.RunStep(self._step)

                pass_flag = True
                pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                    lower_limit=self.lower_limit, raise_exception=False)
                # If pass_flag returned false, means it had convergence error
                if not pass_flag:
                    # change command
                    new_control_command = self.edit_capacitor_settings_for_convergence(control_command)
                    dss.run_command(new_control_command)
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit,
                                                            raise_exception=True)
                    control_command = new_control_command

                self.write_dss_file(control_command)
                if not dss.CapControls.Next() > 0:
                    break
        # if there are caps without cap control add a cap control
        if dss.Capacitors.Count() > len(caps_with_control):
            dss.Capacitors.First()
            while True:
                cap_name = dss.Capacitors.Name()
                if cap_name not in caps_with_control:
                    cap_ctrl_name = "capctrl" + cap_name
                    cap_bus = dss.CktElement.BusNames()[0].split(".")[0]
                    # Get line to be controlled
                    dss.Lines.First()
                    while True:
                        Line_name = dss.Lines.Name()
                        bus1 = dss.Lines.Bus1().split(".")[0]
                        if bus1 == cap_bus:
                            break
                        if not dss.Lines.Next() > 0:
                            break
                    control_command = "New CapControl.{cc} element=Line.{el} terminal={trm} capacitor={cbank} PTRatio={pt} Type={tp}" \
                                      " ONsetting={o} OFFsetting={of} PTphase={ph} Delay={d} DelayOFF={dof} DeadTime={dt} enabled=True".format(
                        cc=cap_ctrl_name,
                        el=Line_name,
                        trm=self.terminal,
                        cbank=cap_name,
                        pt=self.cap_correct_PTratios[cap_name],
                        tp=self.cap_control,
                        o=self.capON,
                        of=self.capOFF,
                        ph=self.PTphase,
                        d=self.capONdelay,
                        dof=self.capOFFdelay,
                        dt=self.capdeadtime
                    )
                    if len(self.cap_initial_settings) > 0 and cap_ctrl_name not in self.cap_initial_settings:
                        self.cap_initial_settings[cap_name] = [self.capON, self.capOFF]
                    dss.run_command(control_command)
                    cap_on_settings_check[cap_name] = self.capON
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)

                    pass_flag = True
                    pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                        lower_limit=self.lower_limit,
                                                                        raise_exception=False)
                    # If pass_flag returned false, means it had convergence error
                    if not pass_flag:
                        # change command
                        new_control_command = self.edit_capacitor_settings_for_convergence(control_command)
                        dss.run_command(new_control_command)
                        self.dssSolver.Solve()
                        self._simulation.RunStep(self._step)
                        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                lower_limit=self.lower_limit,
                                                                raise_exception=True)
                        control_command = new_control_command

                    self.write_dss_file(control_command)
                dss.Circuit.SetActiveElement("Capacitor." + cap_name)
                if not dss.Capacitors.Next() > 0:
                    break

        self.dssSolver.Solve()
        self._simulation.RunStep(self._step)

        # Check whether settings have been applied or not
        if dss.CapControls.Count() > 0:
            dss.CapControls.First()
            while True:
                cap_on = dss.CapControls.ONSetting()
                name = dss.CapControls.Name()
                if abs(cap_on - cap_on_settings_check[cap_name]) > 0.1:
                    self.logger.info("Settings for cap bank %s not implemented", cap_name)
                if not dss.CapControls.Next() > 0:
                    break

        # self.get_nodal_violations()
        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit, lower_limit=self.lower_limit)

    def get_viols_with_initial_cap_settings(self):
        if len(self.cap_initial_settings) > 0:
            for key, vals in self.cap_initial_settings.items():
                dss.CapControls.First()
                while True:
                    cap_name = dss.CapControls.Capacitor()
                    if cap_name == key:
                        dss.CapControls.ONSetting(vals[0])
                        dss.CapControls.OFFSetting(vals[1])
                    if not dss.CapControls.Next() > 0:
                        break
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)
            key = "original"
            self.cap_sweep_res_dict[key] = self.severity_indices[2]

    def cap_settings_sweep(self, upper_limit, lower_limit):
        # This function increases differences between cap ON and OFF voltages in user defined increments,
        #  default 1 volt, until upper and lower bounds are reached.
        self.cap_sweep_res_dict = {}
        self.get_viols_with_initial_cap_settings()
        self.cap_on_setting = self.capON
        self.cap_off_setting = self.capOFF
        self.cap_control_gap = self.config["cap_sweep_voltage_gap"]
        while self.cap_on_setting > lower_limit * self.config[
            "nominal_voltage"] or self.cap_off_setting < upper_limit * self.config[
            "nominal_voltage"]:
            # Apply cap ON and OFF settings and determine their impact
            key = "{}_{}".format(self.cap_on_setting, self.cap_off_setting)
            dss.CapControls.First()
            while True:
                cc_name = dss.CapControls.Name()
                dss.run_command("Edit CapControl.{cc} ONsetting={o} OFFsetting={of}".format(
                    cc=cc_name,
                    o=self.cap_on_setting,
                    of=self.cap_off_setting
                ))
                self.dssSolver.Solve()
                self._simulation.RunStep(self._step)
                if not dss.CapControls.Next() > 0:
                    break
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)
            self.cap_sweep_res_dict[key] = self.severity_indices[2]
            if (self.cap_on_setting - self.cap_control_gap / 2) <= lower_limit * self.config[
                "nominal_voltage"]:
                self.cap_on_setting = lower_limit * self.config["nominal_voltage"]
            else:
                self.cap_on_setting = self.cap_on_setting - self.cap_control_gap / 2
            if (self.cap_off_setting + self.cap_control_gap / 2) >= upper_limit * self.config[
                "nominal_voltage"]:
                self.cap_off_setting = upper_limit * self.config["nominal_voltage"]
            else:
                self.cap_off_setting = self.cap_off_setting + self.cap_control_gap / 2
        self.apply_best_capsetting(upper_limit=self.upper_limit)

    def apply_orig_cap_setting(self):
        for key, vals in self.cap_initial_settings.items():
            dss.CapControls.First()
            while True:
                cap_name = dss.CapControls.Capacitor()
                if cap_name == key:
                    command_string = "Edit CapControl.{ccn} ONsetting={o} OFFsetting={of} !original".format(
                        ccn=dss.CapControls.Name(),
                        o=vals[0],
                        of=vals[1]
                    )
                    dss.run_command(command_string)
                    self.write_dss_file(command_string)
                if not dss.CapControls.Next() > 0:
                    break
        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                lower_limit=self.lower_limit)

    def apply_best_capsetting(self, upper_limit):
        best_setting = ''
        # Start with assumption that each node has a violation at all time points and each violation if outside bounds
        #  by upper voltage limit - basically the maximum possible severity
        min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * upper_limit
        for key, val in self.cap_sweep_res_dict.items():
            if val < min_severity:
                min_severity = val
                best_setting = key
        # Apply best settings which give minimum severity index
        if best_setting == "original":
            self.apply_orig_cap_setting()
        else:
            best_on_setting = best_setting.split("_")[0]
            best_off_setting = best_setting.split("_")[1]
            dss.CapControls.First()
            while True:
                cc_name = dss.CapControls.Name()
                command_string = ("Edit CapControl.{cc} ONsetting={o} OFFsetting={of}".format(
                    cc=cc_name,
                    o=best_on_setting,
                    of=best_off_setting
                ))
                dss.run_command(command_string)
                self.write_dss_file(command_string)
                self.dssSolver.Solve()
                self._simulation.RunStep(self._step)
                if not dss.CapControls.Next() > 0:
                    break
        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                lower_limit=self.lower_limit)

    def edit_capacitor_settings_for_convergence(self, control_command):
        new_deadtime = 50
        new_delay = 50
        self.capON = round((self.config["nominal_voltage"] - (self.config["cap_sweep_voltage_gap"]+1) / 2), 1)
        self.capOFF = round((self.config["nominal_voltage"] + (self.config["cap_sweep_voltage_gap"]+1) / 2), 1)
        self.logger.info("Changed Initial On and Off Cap settings to avoid convergence issues ")

        new_capON = self.capON
        new_capOFF = self.capOFF

        new_control_command = control_command
        # self.remove_line_from_dss_file(control_command)  # remove command that caused convergence issue
        control_command = control_command.replace('New', 'Edit')
        control_command = re.sub("enabled=True", "enabled=False", control_command)
        dss.run_command(control_command)  # disable and run previous control command

        new_control_command = re.sub("DeadTime=\d+", 'DeadTime=' + str(new_deadtime), new_control_command)
        new_control_command = re.sub("Delay=\d+", 'Delay=' + str(new_delay), new_control_command)
        new_control_command = re.sub("ONsetting=\d+\.\d+", 'ONsetting=' + str(new_capON), new_control_command)
        new_control_command = re.sub("OFFsetting=\d+\.\d+", 'OFFsetting=' + str(new_capOFF), new_control_command)
        return new_control_command

    def write_dss_file(self, device_command):
        self.dss_upgrades.append(device_command + "\n")
        return

    def write_upgrades_to_file(self, output_path=None):
        if output_path is None:
            output_path = os.path.join(self.config["Outputs"], "voltage_upgrades.dss")
        with open(output_path, "w") as datafile:
            for line in self.dss_upgrades:
                datafile.write(line)
        return

    def reg_controls_sweep(self, upper_limit, lower_limit):
        self.vsps = []
        v = lower_limit * self.config["nominal_voltage"]
        while v < upper_limit * self.config["nominal_voltage"]:
            self.vsps.append(v)
            v += self.config["reg_v_delta"]
        for reg_sp in self.vsps:
            for bandw in self.config["reg_control_bands"]:
                dss.RegControls.First()
                while True:
                    regctrl_name = dss.RegControls.Name()
                    xfmr = dss.RegControls.Transformer()
                    dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                    xfmr_buses = dss.CktElement.BusNames()
                    xfmr_b1 = xfmr_buses[0].split(".")[0]
                    xfmr_b2 = xfmr_buses[1].split(".")[0]
                    # Skipping over substation LTC if it exists
                    # for n, d in self.G.in_degree().items():
                    #     if d == 0:
                    #         sourcebus = n
                    sourcebus = self.source
                    if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                        dss.Circuit.SetActiveElement("Regcontrol.{}".format(regctrl_name))
                        if not dss.RegControls.Next() > 0:
                            break
                        continue
                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(regctrl_name))

                    command_string = "Edit Regcontrol.{rn} vreg={sp} band={b}".format(
                        rn=regctrl_name,
                        sp=reg_sp,
                        b=bandw
                    )
                    dss.run_command(command_string)
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    if not dss.RegControls.Next() > 0:
                        break
                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                        lower_limit=self.lower_limit)
                self.reg_sweep_viols["{}_{}".format(str(reg_sp), str(bandw))] = self.severity_indices[2]
        self.apply_best_regsetting(upper_limit=self.upper_limit)

    def apply_best_regsetting(self, upper_limit):
        # TODO: Remove substation LTC from the settings sweep
        best_setting = ''
        # Start with assumption that each node has a violation at all time points and each violation if outside bounds
        #  by upper voltage limit - basically the maximum possible severity
        min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * upper_limit
        for key, val in self.reg_sweep_viols.items():
            if val < min_severity:
                min_severity = val
                best_setting = key
        if best_setting == "original":
            self.apply_orig_reg_setting()
        else:
            self.v_sp = best_setting.split("_")[0]
            self.reg_band = best_setting.split("_")[1]
            dss.RegControls.First()
            while True:
                reg_ctrl_nm = dss.RegControls.Name()
                xfmr = dss.RegControls.Transformer()
                dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                xfmr_buses = dss.CktElement.BusNames()
                xfmr_b1 = xfmr_buses[0].split(".")[0]
                xfmr_b2 = xfmr_buses[1].split(".")[0]
                dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_ctrl_nm))
                # Skipping over substation LTC if it exists
                # for n, d in self.G.in_degree().items():
                #     if d == 0:
                #         sourcebus = n
                sourcebus = self.source
                if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_ctrl_nm))
                    if not dss.RegControls.Next() > 0:
                        break
                    continue
                command_string = "Edit RegControl.{rn} vreg={sp} band={b}".format(
                    rn=reg_ctrl_nm,
                    sp=self.v_sp,
                    b=self.reg_band,
                )
                dss.run_command(command_string)
                self.dssSolver.Solve()
                self._simulation.RunStep(self._step)
                if self.write_flag == 1:
                    self.write_dss_file(command_string)
                if not dss.RegControls.Next() > 0:
                    break

    def apply_orig_reg_setting(self):
        for key, vals in self.initial_regctrls_settings.items():
            self.v_sp = vals[0]
            self.reg_band = vals[1]
            dss.Circuit.SetActiveElement("RegControl.{}".format(key))
            command_string = "Edit RegControl.{rn} vreg={sp} band={b} !original".format(
                rn=key,
                sp=vals[0],
                b=vals[1],
            )
            dss.run_command(command_string)
            self.dssSolver.Solve()
            self._simulation.RunStep(self._step)
            if self.write_flag == 1:
                self.write_dss_file(command_string)

    def add_substation_LTC(self):
        # This function identifies whether or not a substation LTC exists - if not adds one along with a new sub xfmr
        # if required -  if one exists corrects its settings
        # Identify source bus
        # It seems that networkx in a directed graph only counts edges incident on a node towards degree.
        #  This is why source bus is the only bus which has a degree of zero
        # for n, d in self.G.in_degree().items():
        #     if d == 0:
        #         self.source = n

        # Identify whether a transformer is connected to this bus or not
        self.subxfmr = ''
        dss.Transformers.First()
        while True:
            bus_names = dss.CktElement.BusNames()
            from_bus = bus_names[0].split('.')[0].lower()
            to_bus = bus_names[1].split('.')[0].lower()
            if from_bus == self.source or to_bus == self.source:
                self.subxfmr = dss.Transformers.Name()
                self.sub_LTC_bus = to_bus
                break
            if not dss.Transformers.Next() > 0:
                break

        if self.subxfmr == '':
            # Add new transformer if no transformer is connected to source bus, then add LTC
            self.add_new_xfmr(self.source)
            self.write_flag = 1
            self.add_new_regctrl(self.source)
        elif self.subxfmr != '':
            # add LTC onto existing substation transformer
            self.write_flag = 1
            self.add_new_regctrl(self.sub_LTC_bus)
        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                lower_limit=self.lower_limit)
        return

    def add_new_xfmr(self, node):
        # If substation does not have a transformer add a transformer at the source bus so a new reg
        # control object may be created -  after the transformer and reg control have been added the feeder would have
        #  to be re compiled as system admittance matrix has changed
        # Find line to which this node is connected to
        # node = node.lower()
        degree = 1
        if node.lower() == self.source.lower():
            degree = 0

        dss.Lines.First()
        while True:
            # For sub LTC
            if degree == 0:
                if dss.Lines.Bus1().split(".")[0] == node:
                    bus1 = dss.Lines.Bus1()
                    bus2 = dss.Lines.Bus2()
                    new_node = "Regctrl_" + bus2
                    xfmr_name = "New_xfmr_" + node
                    line_name = dss.Lines.Name()
                    phases = dss.Lines.Phases()
                    amps = dss.CktElement.NormalAmps()
                    dss.Circuit.SetActiveBus(bus1)
                    x = dss.Bus.X()
                    y = dss.Bus.Y()
                    dss.Circuit.SetActiveBus(bus2)
                    kV_node = dss.Bus.kVBase()
                    if phases > 1:
                        kV_DT = kV_node * 1.732
                        kVA = int(kV_DT * amps * 1.1)  # 10% over sized transformer - ideally we
                        # would use an auto transformer which would need a much smaller kVA rating
                        command_string = "New Transformer.{xfn} phases={p} windings=2 buses=({b1},{b2}) conns=({cntp},{cntp})" \
                                         " kvs=({kv},{kv}) kvas=({kva},{kva}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001" \
                                         " Maxtap=1.1 Mintap=0.9 enabled=True".format(
                            xfn=xfmr_name,
                            p=phases,
                            b1=bus1,
                            b2=new_node,
                            cntp=self.reg_conn,
                            kv=kV_DT,
                            kva=kVA
                        )
                    elif phases == 1:
                        kVA = int(kV_node * amps * 1.1)  # 10% over sized transformer - ideally we
                        # would use an auto transformer which would need a much smaller kVA rating
                        # make bus1 of line as reg ctrl node
                        command_string = "New Transformer.{xfn} phases={p} windings=2 buses=({b1},{b2}) conns=({cntp},{cntp})" \
                                         " kvs=({kv},{kv}) kvas=({kva},{kva}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001" \
                                         " Maxtap=1.1 Mintap=0.9 enabled=True".format(
                            xfn=xfmr_name,
                            p=phases,
                            b1=bus1,
                            b2=new_node,
                            cntp=self.reg_conn,
                            kv=kV_node,
                            kva=kVA
                        )
                    control_command = "Edit Line.{} bus1={}".format(line_name, new_node)
                    dss.run_command(control_command)
                    if self.write_flag == 1:
                        self.write_dss_file(control_command)
                    dss.run_command(command_string)
                    if self.write_flag == 1:
                        self.write_dss_file(command_string)
                    # Update system admittance matrix
                    dss.run_command("CalcVoltageBases")
                    dss.Circuit.SetActiveBus(new_node)
                    dss.Bus.X(x)
                    dss.Bus.Y(y)
                    if self.write_flag == 1:
                        self.write_dss_file("//{},{},{}".format(new_node.split(".")[0], x, y))
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    self.generate_nx_representation()
                    dss.Circuit.SetActiveElement("Line." + line_name)
                    break
            # For regulator
            elif degree > 0:
                if dss.Lines.Bus2().split(".")[0] == node:
                    bus1 = dss.Lines.Bus1()
                    bus2 = dss.Lines.Bus2()
                    new_node = "Regctrl_" + bus2
                    xfmr_name = "New_xfmr_" + node
                    line_name = dss.Lines.Name()
                    phases = dss.Lines.Phases()
                    amps = dss.CktElement.NormalAmps()
                    dss.Circuit.SetActiveBus(bus2)
                    x = dss.Bus.X()
                    y = dss.Bus.Y()
                    kV_node = dss.Bus.kVBase()
                    if phases > 1:
                        kV_DT = kV_node * 1.732
                        kVA = int(kV_DT * amps * 1.1)  # 10% over sized transformer - ideally we
                        # would use an auto transformer which would need a much smaller kVA rating

                        command_string = "New Transformer.{xfn} phases={p} windings=2 buses=({b1},{b2}) conns=(wye,wye)" \
                                         " kvs=({kv},{kv}) kvas=({kva},{kva}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001" \
                                         " Maxtap=1.1 Mintap=0.9 enabled=True".format(
                            xfn=xfmr_name,
                            p=phases,
                            b1=new_node,
                            b2=bus2,
                            kv=kV_DT,
                            kva=kVA
                        )
                    elif phases == 1:
                        kVA = int(kV_node * amps * 1.1)  # 10% over sized transformer - ideally we
                        # would use an auto transformer which would need a much smaller kVA rating
                        command_string = "New Transformer.{xfn} phases={p} windings=2 buses=({b1},{b2}) conns=(wye,wye)" \
                                         " kvs=({kv},{kv}) kvas=({kva},{kva}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001" \
                                         " Maxtap=1.1 Mintap=0.9 enabled=True".format(
                            xfn=xfmr_name,
                            p=phases,
                            b1=new_node,
                            b2=bus2,
                            kv=kV_node,
                            kva=kVA
                        )
                    control_command = "Edit Line.{} bus2={}".format(line_name, new_node)
                    dss.run_command(control_command)
                    if self.write_flag == 1:
                        self.write_dss_file(control_command)
                    dss.run_command(command_string)
                    if self.write_flag == 1:
                        self.write_dss_file(command_string)
                    # Update system admittance matrix
                    dss.run_command("CalcVoltageBases")
                    dss.Circuit.SetActiveBus(new_node)
                    dss.Bus.X(x)
                    dss.Bus.Y(y)
                    if self.write_flag == 1:
                        self.write_dss_file("//{},{},{}".format(new_node.split(".")[0], x, y))
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    self.generate_nx_representation()
                    dss.Circuit.SetActiveElement("Line." + line_name)
                    break
            if not dss.Lines.Next() > 0:
                break

        return

    def add_new_regctrl(self, node):
        # Identify whether or not a reg contrl exists at the transformer connected to this bus - a transformer should
        # definitely exist by now. If it does correct its settings else add a new reg ctrl with correct settings
        # If transformer exists check if it already has a reg control object
        if dss.Transformers.Count() > 0:
            dss.Transformers.First()
            while True:
                # Identify transformer connected to this node
                bus_prim = dss.CktElement.BusNames()[0].split(".")[0]
                bus_sec = dss.CktElement.BusNames()[1].split(".")[0]
                if bus_prim == node or bus_sec == node:
                    xfmr_name = dss.Transformers.Name()
                    phases = dss.CktElement.NumPhases()
                    dss.Circuit.SetActiveBus(node)
                    # node info is only used to get correct kv values
                    kV = dss.Bus.kVBase()
                    winding = self.LTC_wdg
                    vreg = self.LTC_setpoint
                    reg_delay = self.LTC_delay
                    deadband = self.LTC_band
                    pt_ratio = kV * 1000 / (self.config["nominal_voltage"])

                    xfmr_regctrl = ''

                    # Identify whether a reg control exists on this transformer
                    if dss.RegControls.Count() > 0:
                        dss.RegControls.First()
                        while True:
                            xfmr_name_reg = dss.RegControls.Transformer()
                            if xfmr_name_reg == xfmr_name:
                                # if reg control already exists correct its settings
                                xfmr_regctrl = dss.RegControls.Name()
                                command_string = "Edit RegControl.{rn} transformer={tn} winding={w} vreg={sp} ptratio={rt} band={b} " \
                                                 "enabled=true delay={d}".format(
                                    rn=xfmr_regctrl,
                                    tn=xfmr_name,
                                    w=winding,
                                    sp=vreg,
                                    rt=pt_ratio,
                                    b=deadband,
                                    d=reg_delay
                                )
                                dss.run_command(command_string)
                                self.dssSolver.Solve()
                                self._simulation.RunStep(self._step)
                                dss.run_command("Calcvoltagebases")
                                # add this to a dss_upgrades.dss file
                                if self.write_flag == 1:
                                    self.write_dss_file(command_string)
                                # check for violations
                                # self.get_nodal_violations()
                                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                        lower_limit=self.lower_limit)
                                break
                            if not dss.RegControls.Next() > 0:
                                break
                    if xfmr_regctrl == '':
                        # if reg control does not exist on the transformer add one
                        xfmr_regctrl = "New_regctrl_" + node
                        command_string = "New RegControl.{rn} transformer={tn} winding={w} vreg={sp} ptratio={rt} band={b} " \
                                         "enabled=true delay={d}".format(
                            rn=xfmr_regctrl,
                            tn=xfmr_name,
                            w=winding,
                            sp=vreg,
                            rt=pt_ratio,
                            b=deadband,
                            d=reg_delay
                        )
                        dss.run_command(command_string)
                        self.dssSolver.Solve()
                        self._simulation.RunStep(self._step)
                        dss.run_command("CalcVoltageBases")
                        # add this to a dss_upgrades.dss file
                        if self.write_flag == 1:
                            self.write_dss_file(command_string)
                        # check for violations
                        # self.get_nodal_violations()
                        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                lower_limit=self.lower_limit)
                        break
                    dss.Circuit.SetActiveElement("Transformer." + xfmr_name)
                if not dss.Transformers.Next() > 0:
                    break
        return

    def LTC_controls_sweep(self, upper_limit, lower_limit):
        self.vsps = []
        v = lower_limit * self.config["nominal_voltage"]
        while v < upper_limit * self.config["nominal_voltage"]:
            self.vsps.append(v)
            v += self.config["reg_v_delta"]
        for reg_sp in self.vsps:
            for bandw in self.config["reg_control_bands"]:
                dss.RegControls.First()
                while True:
                    regctrl_name = dss.RegControls.Name()
                    xfmr = dss.RegControls.Transformer()
                    dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                    xfmr_buses = dss.CktElement.BusNames()
                    xfmr_b1 = xfmr_buses[0].split(".")[0]
                    xfmr_b2 = xfmr_buses[1].split(".")[0]
                    # Skipping over substation LTC if it exists
                    # for n, d in self.G.in_degree().items():
                    #     if d == 0:
                    #         sourcebus = n
                    sourcebus = self.source
                    if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                        dss.Circuit.SetActiveElement("Regcontrol.{}".format(regctrl_name))
                        command_string = "Edit Regcontrol.{rn} vreg={sp} band={b}".format(
                            rn=regctrl_name,
                            sp=reg_sp,
                            b=bandw
                        )
                        dss.run_command(command_string)
                        self.dssSolver.Solve()
                        self._simulation.RunStep(self._step)
                        pass_flag = True
                        pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                            lower_limit=self.lower_limit,
                                                                            raise_exception=False)

                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(regctrl_name))
                    if not dss.RegControls.Next() > 0:
                        break
                self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                        lower_limit=self.lower_limit)
                self.subLTC_sweep_viols["{}_{}".format(str(reg_sp), str(bandw))] = self.severity_indices[2]
        self.apply_best_LTCsetting(upper_limit=self.upper_limit)

    def apply_best_LTCsetting(self, upper_limit):
        # TODO: Remove substation LTC from the settings sweep
        best_setting = ''
        # Start with assumption that each node has a violation at all time points and each violation if outside bounds
        #  by upper voltage limit - basically the maximum possible severity
        min_severity = 10000000000000
        # TODO - below logic for min_severity was used previously - however, error cases were encountered
        #  for some feeders due to min_severity being not large enough
        # min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * upper_limit
        self.logger.info(f"Severity: {pow(len(self.all_bus_names), 2) * len(self.config['tps_to_test']) * upper_limit}")
        self.logger.debug(self.subLTC_sweep_viols)
        for key, val in self.subLTC_sweep_viols.items():
            if val < min_severity:
                min_severity = val
                best_setting = key
        if best_setting == "original":
            self.apply_orig_LTC_setting()
        else:
            self.logger.debug("Best_setting: %s", best_setting)
            v_sp = best_setting.split("_")[0]
            reg_band = best_setting.split("_")[1]
            dss.RegControls.First()
            while True:
                reg_ctrl_nm = dss.RegControls.Name()
                xfmr = dss.RegControls.Transformer()
                dss.Circuit.SetActiveElement("Transformer.{}".format(xfmr))
                xfmr_buses = dss.CktElement.BusNames()
                xfmr_b1 = xfmr_buses[0].split(".")[0]
                xfmr_b2 = xfmr_buses[1].split(".")[0]
                # # Skipping over substation LTC if it exists
                # for n, d in self.G.in_degree().items():
                #     if d == 0:
                #         sourcebus = n
                sourcebus = self.source
                if xfmr_b1.lower() == sourcebus.lower() or xfmr_b2.lower() == sourcebus.lower():
                    dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_ctrl_nm))

                    command_string = "Edit RegControl.{rn} vreg={sp} band={b}".format(
                        rn=reg_ctrl_nm,
                        sp=v_sp,
                        b=reg_band,
                    )
                    dss.run_command(command_string)
                    self.dssSolver.Solve()
                    self._simulation.RunStep(self._step)
                    pass_flag = True
                    pass_flag = self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                                        lower_limit=self.lower_limit,
                                                                        raise_exception=False)
                    # TODO : add code to change settings if there is a convergence error
                    if pass_flag:
                        self.write_dss_file(command_string)
                    else:
                        self.apply_orig_LTC_setting()

                dss.Circuit.SetActiveElement("Regcontrol.{}".format(reg_ctrl_nm))
                if not dss.RegControls.Next() > 0:
                    break
        self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                lower_limit=self.lower_limit)

    def apply_orig_LTC_setting(self):
        for key, vals in self.initial_subLTC_settings.items():
            dss.Circuit.SetActiveElement("RegControl.{}".format(key))
            command_string = "Edit RegControl.{rn} vreg={sp} band={b} !original".format(
                rn=key,
                sp=vals[0],
                b=vals[1],
            )
            dss.run_command(command_string)
            self.dssSolver.Solve()
            self._simulation.RunStep(self._step)
            self.write_dss_file(command_string)

    def get_shortest_path(self):
        new_graph = self.G.to_undirected()
        precal_paths = []
        self.UT_paths_dict = {}
        # Get upper triangular distance matrix - reduces computational time by half
        for bus1 in self.buses_with_violations:
            self.UT_paths_dict[bus1] = []
            for bus_n in self.buses_with_violations:
                if bus_n == bus1:
                    path_length = 0.0
                elif bus_n in precal_paths:
                    continue
                else:
                    path = nx.shortest_path(new_graph, source=bus1, target=bus_n)
                    path_length = 0.0
                    for nodes_count in range(len(path) - 1):
                        path_length += float(new_graph[path[nodes_count + 1]][path[nodes_count]]['length'])
                self.UT_paths_dict[bus1].append(round(path_length, 3))
            precal_paths.append(bus1)

    def get_full_distance_dict(self):
        self.square_array = []
        self.square_dict = {}
        self.cluster_nodes_list = []
        temp_nodes_list = []
        ll = []
        max_length = 0
        for key, values in self.UT_paths_dict.items():
            self.cluster_nodes_list.append(key)
            if len(values) > max_length:
                max_length = len(values)
        # Create a square dict with zeros for lower triangle values
        for key, values in self.UT_paths_dict.items():
            temp_nodes_list.append(key)
            temp_list = []
            if len(values) < max_length:
                new_items_req = max_length - len(values)
                for items_cnt in range(0, new_items_req, 1):
                    temp_list.append(0.0)
            for item in values:
                temp_list.append(float(item))
            self.square_dict[key] = temp_list
        # Replace lower triangle zeros with upper triangle values
        key_count = 0
        for key, values in self.UT_paths_dict.items():
            for items_count in range(len(values)):
                self.square_dict[temp_nodes_list[items_count]][key_count] = values[items_count]
            key_count += 1
            temp_nodes_list.remove(key)
        # from dict create a list of lists
        for key, values in self.square_dict.items():
            ll.append(values)
        # Create numpy array from list of lists
        self.square_array = np.array(ll)

    def plot_heatmap_distmatrix(self):
        # seaborn has been removed from the package because the developers expect that
        # this code is unused.
        if not _SEABORN_IMPORTED:
            raise Exception("seaborn must be installed for this function")
        plt.figure(figsize=(7, 7))
        ax = sns.heatmap(self.square_array, linewidth=0.5)
        plt.title("Distance matrix of nodes with violations")
        plt.savefig(os.path.join(self.config["Outputs"],"Nodal_violations_heatmap.pdf"))

    def cluster_square_array(self):
        # Clustering the distance matrix into clusters equal to optimal clusters
        if self.config["create_topology_plots"]:
            self.plot_heatmap_distmatrix()
        for self.optimal_clusters in range(1, self.max_regs + 1, 1):
            self.no_reg_flag = 0
            self.clusters_dict = {}
            model = AgglomerativeClustering(n_clusters=self.optimal_clusters, affinity='euclidean', linkage='ward')
            model.fit(self.square_array)
            labels = model.labels_
            for lab in range(len(labels)):
                if labels[lab] not in self.clusters_dict:
                    self.clusters_dict[labels[lab]] = [self.cluster_nodes_list[lab]]
                else:
                    self.clusters_dict[labels[lab]].append(self.cluster_nodes_list[lab])
            self.identify_correct_reg_node()
            self.add_new_reg_common_nodes(upper_limit=self.upper_limit)
            if self.no_reg_flag == 1:
                continue
            self.write_flag = 0
            self.reg_controls_sweep(upper_limit=self.upper_limit, lower_limit=self.lower_limit)
            self.write_flag = 1
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)
            self.cluster_optimal_reg_nodes[self.optimal_clusters] = [self.severity_indices[2],
                                                                     [self.v_sp, self.reg_band], []]
            # Store all optimal nodes for a given number of clusters
            for key, vals in self.upstream_reg_node.items():
                self.cluster_optimal_reg_nodes[self.optimal_clusters][2].append(vals)
            if self.config["create_topology_plots"]:
                self.plot_created_clusters()
                self.plot_violations()
            self.logger.info("max_V_viol=%s, min_V_viol=%s, severity_indices=%s",
                             self.max_V_viol, self.min_V_viol, self.severity_indices)
            self.disable_regctrl_current_cluster()
            if (len(self.buses_with_violations)) == 0:
                self.logger.info("All nodal violations have been removed successfully.....quitting")
                break

    def disable_regctrl_current_cluster(self):
        disable_index = self.optimal_clusters
        if disable_index in self.cluster_optimal_reg_nodes:
            for node in self.cluster_optimal_reg_nodes[disable_index][2]:
                self.write_flag = 0
                self.disable_added_xfmr(node)
                self.write_flag = 1
                command_string = "Edit RegControl.{rn} enabled=False".format(
                    rn="New_regctrl_" + node
                )
                dss.run_command(command_string)
                # self.write_dss_file(command_string)
        return

    def disable_added_xfmr(self, node):
        # Unfortunately since OpenDSS disables by transformer by opening the circuit instead of creating a short circuit,
        # this function will remove the transformer by first disabling it, then it will connect the line properly to
        # remove the islands
        # Substation will always have a xfmr by this point so only regulator transformers have to be removed

        transformer_name = "New_xfmr_" + node

        dss.Transformers.First()
        while True:
            if dss.Transformers.Name().lower() == transformer_name.lower():
                prim_bus = dss.CktElement.BusNames()[0].split(".")[0]
                sec_bus = dss.CktElement.BusNames()[1]
                command_string = "Edit Transformer.{xfmr} enabled=False".format(xfmr=transformer_name)
                dss.run_command(command_string)
                if self.write_flag == 1:
                    self.write_dss_file(command_string)
                command_string = "Edit Transformer.{xfmr} buses=({b1},{b2})".format(
                    xfmr=transformer_name,
                    b1=dss.CktElement.BusNames()[0],
                    b2=dss.CktElement.BusNames()[0]
                )
                dss.run_command(command_string)
                if self.write_flag == 1:
                    self.write_dss_file(command_string)
                dss.Lines.First()
                while True:
                    if dss.Lines.Bus2().split(".")[0].lower() == prim_bus.lower():
                        command_string = "Edit Line.{ln} bus2={b}".format(
                            ln=dss.Lines.Name(),
                            b=sec_bus
                        )
                        dss.run_command(command_string)
                        if self.write_flag == 1:
                            self.write_dss_file(command_string)
                        # Update system admittance matrix
                        dss.run_command("CalcVoltageBases")
                        self.dssSolver.Solve()
                        self._simulation.RunStep(self._step)
                        self.generate_nx_representation()
                        break
                    if not dss.Lines.Next() > 0:
                        break
                break
            if not dss.Transformers.Next() > 0:
                break
        return

    def add_new_reg_common_nodes(self, upper_limit):
        # Identify whether a transformer exists at this node or not. If yes simply add a new reg control -
        # in fact calling the add_new_regctrl function will automatically check whether a reg control exists or not
        # -  so only thing to be ensured is that a transformer should exist - for next time when this function is called
        #  a new set of clusters will be passed
        self.upstream_reg_node = {}
        for cluster, common_nodes in self.upstream_nodes_dict.items():
            self.vdev_cluster_nodes = {}
            for node in common_nodes:
                continue_flag = 0
                # Here do not add a new reg control to source bus as it already has a LTC
                # for n, d in self.G.in_degree().items():
                #     if n == node and d==0:
                if node.lower() == self.source.lower():
                    continue_flag = 1
                if continue_flag == 1:
                    continue
                dss.Transformers.First()
                xfmr_flag = 0
                while True:
                    xfmr_name = dss.Transformers.Name()
                    # dss.Circuit.SetActiveElement("Transformer."+xfmr_name)
                    prim_bus = dss.CktElement.BusNames()[0].split(".")[0]
                    sec_bus = dss.CktElement.BusNames()[1].split(".")[0]
                    if node == sec_bus or node == prim_bus:
                        xfmr_flag = 1
                        break
                    if not dss.Transformers.Next() > 0:
                        break
                if xfmr_flag == 0:
                    self.write_flag = 0
                    self.add_new_xfmr(node)
                    # These are just trial settings and do not have to be written in the output file
                    self.add_new_regctrl(node)
                    self.write_flag = 1
                elif xfmr_flag == 1:
                    # The reason is that we are skipping over LTC node already, and all other other nodes with
                    # pre-existing xfmrs will be primary to secondary DTs which we do not want to control as regs are
                    # primarily in line and not on individual distribution transformers
                    continue
                self.vdev_cluster_nodes[node] = self.severity_indices[2]
                # self.get_nodes_withV(node)
                # Now disable the added regulator control and remove the added transformer
                if xfmr_flag == 0:
                    command_string = "Edit RegControl.{rn} enabled=No".format(
                        rn="New_regctrl_" + node
                    )
                    dss.run_command(command_string)
                    self.write_flag = 0
                    self.disable_added_xfmr(node)
                    self.write_flag = 1
            # For a given cluster identify the node which leads to minimum number of buses with violations
            min_severity = 1000000000
            # TODO - below logic for min_severity was used previously - however, error cases were encountered
            #  for some feeders due to min_severity being not large enough
            # min_severity = pow(len(self.all_bus_names), 2) * len(self.config["tps_to_test"]) * upper_limit
            min_node = ''
            for key, value in self.vdev_cluster_nodes.items():
                if value <= min_severity:
                    min_severity = value
                    min_node = key
            self.logger.info("Min node is: %s", min_node)
            # If no nodes is found break the loop and go to next number of clusters:
            if min_node == '':
                continue
            self.upstream_reg_node[cluster] = min_node
            # Since this is an optimal location add the transformer here - this transformer will stay as long as
            # self.optimal_clusters does not increment. If this parameter changes then all devices at nodes mentioned
            # in previous optimal cluster number in self.cluster_optimal_reg_nodes should be disabled
            self.write_flag = 0
            self.add_new_xfmr(min_node)
            self.write_flag = 1
            command_string = "Edit RegControl.{rn} enabled=True".format(
                rn="New_regctrl_" + min_node
            )
            dss.run_command(command_string)
            self.dssSolver.Solve()
            self._simulation.RunStep(self._step)
            self.check_voltage_violations_multi_tps(upper_limit=self.upper_limit,
                                                    lower_limit=self.lower_limit)
            # Even here we do not need to write out the setting as the only setting to be written would
            # self.write_dss_file(command_string)
        # if no reg control nodes are found then continue
        if len(self.upstream_reg_node) == 0:
            self.no_reg_flag = 1

        return

    def identify_correct_reg_node(self):
        # In this function the very first common upstream node and all upstream nodes for all members of the
        #  cluster are stored
        # TODO: include some type of optimization - such as look at multiple upstream nodes and place where sum of
        # TODO: downstream node voltage deviations is minimum as long as it doesn't overlap with other clusters
        # Currently it only identifies the common upstream nodes for all cluster nodes
        self.upstream_nodes_dict = {}

        temp_graph = self.G
        new_graph = temp_graph.to_undirected()
        for key, items in self.clusters_dict.items():
            paths_dict_cluster = {}
            common_nodes = []
            for buses in items:
                path = nx.shortest_path(new_graph, source=self.source, target=buses)
                paths_dict_cluster[buses] = path
            for common_bus in path:
                flag = 1
                for bus, paths in paths_dict_cluster.items():
                    if common_bus not in paths:
                        flag = 0
                        break
                if flag == 1:
                    common_nodes.append(common_bus)
            self.upstream_nodes_dict[key] = common_nodes
            # self.upstream_reg_node[key] = common_nodes[-1]
        return

    def plot_created_clusters(self):
        plt.figure(figsize=(7, 7))
        # Plots clusters and common paths from clusters to source
        plt.clf()
        self.pos_dict = nx.get_node_attributes(self.G, 'pos')
        ec = nx.draw_networkx_edges(self.G, pos=self.pos_dict, alpha=1.0, width=0.3)
        ld = nx.draw_networkx_nodes(self.G, pos=self.pos_dict, nodelist=self.cluster_nodes_list, node_size=2,
                                    node_color='b')
        # Show min V violations
        col = 0
        try:
            for key, values in self.clusters_dict.items():
                nodal_violations_pos = {}
                common_nodes_pos = {}
                reg_nodes_pos = {}
                for cluster_nodes in values:
                    nodal_violations_pos[cluster_nodes] = self.pos_dict[cluster_nodes]
                for common_nodes in self.upstream_nodes_dict[key]:
                    common_nodes_pos[common_nodes] = self.pos_dict[common_nodes]
                self.logger.info("%s", self.upstream_reg_node[key])
                reg_nodes_pos[self.upstream_reg_node[key]] = self.pos_dict[self.upstream_reg_node[key]]
                nx.draw_networkx_nodes(self.G, pos=nodal_violations_pos,
                                       nodelist=values, node_size=5, node_color='C{}'.format(col))
                nx.draw_networkx_nodes(self.G, pos=common_nodes_pos,
                                       nodelist=self.upstream_nodes_dict[key], node_size=5,
                                       node_color='C{}'.format(col), alpha=0.3)
                nx.draw_networkx_nodes(self.G, pos=reg_nodes_pos,
                                       nodelist=[self.upstream_reg_node[key]], node_size=25, node_color='r')
                col += 1
        except:
            pass
        plt.axis("off")
        plt.title("All buses with violations grouped in {} clusters".format(self.optimal_clusters))
        plt.savefig(
            os.path.join(self.config["Outputs"], "Cluster_{}_reglocations.pdf".format(str(self.optimal_clusters))))

    def run(self, step, stepMax, simulation=None):
        self.logger.info('Running voltage upgrade post process')
        self._simulation = simulation
        self._step = step
        try:
            self._run()
            has_converged = self.has_converged
            error = self.error

            return step, has_converged, error
        finally:
            self._simulation = None
            self._step = None

    def finalize(self):
        pass

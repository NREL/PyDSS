from PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
# Additional packages
import os
import matplotlib.pyplot as plt
import csv
import pandas as pd
import math
import opendssdirect as dss
import networkx as nx
import time
import json
# from place_new_regs import place_new_regs
import numpy as np
import seaborn as sns
import scipy.spatial.distance as ssd
from sklearn.cluster import AgglomerativeClustering
import matplotlib.image as mpimg
from PyDSS.pyPostprocessor.PostprocessScripts.postprocess_thermal_upgrades import postprocess_thermal_upgrades
plt.rcParams.update({'font.size': 14})

# For an overloaded line if a sensible close enough line code is available then simply change the line code
#  else add a new line in parallel
# Does not correct switch thermal violations if any - will only work on line objects which are not marked as switches
# In this part of the code since lines and DTs
# The available upgrades options can be read from an external library as well, currently being created by reading
#  through the DTs and lines available in the feeder itself.
# TODO: Add xhl, xht, xlt and buses functionality for DTs
# TODO: Units of the line and transformers

class AutomatedThermalUpgrade(AbstractPostprocess):
    """The class is used to induce faults on bus for dynamic simulation studies. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class. 

    :param FaultObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type FaultObj: class:`PyDSS.dssElement.dssElement`
    :param Settings: A dictionary that defines the settings for the faul controller.
    :type Settings: dict
    :param dssInstance: An :class:`opendssdirect` instance
    :type dssInstance: :class:`opendssdirect` instance
    :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit ojects
    :type ElmObjectList: dict
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`
    :raises: AssertionError  if 'FaultObj' is not a wrapped OpenDSS Fault element

    """
    def __init__(self, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
        """Constructor method
        """
        super(AutomatedThermalUpgrade).__init__()
        self.Settings = simulationSettings
        # New settings to be added into simulationsettings
        New_settings = {
            "Feeder": "../Test_Feeder",  # "../Test_Feeder_J1",
            "img_path": "../Images",
            "DPV_scenarios": "../ten_random",  # "../ten_random_J1",
            "master file": "Master_noPV.dss",  # "Master.dss",
            "DPV_penetration_HClimit": 0,
            "DPV_penetration_target": 0,
            "DPV_penetration_step": 10,
            "DPV control": "PF=1",  # "PF=1" or "PF=-0.95" or "VVar-CatA" or "VVar-CatB" or "VVar-VWatt-CatB"
            "DPV system priority": "watt",  # "watt" or "var"
            "Outputs": r"C:\Documents_NREL\Grid_Cost_DER_PhaseII\Control_device_placement\Outputs",
            "line loading limit": 1.0,  # 1=100%
            "DT loading limit": 1.0,  # 1=100%,
            "line_safety_margin": 1.5,# 1.1=110%: implies new line added should be rated at least 10% above the DTs actual overloading
            "xfmr_safety_margin": 1.5,# 1.1=110%: implies new DT added should be rated at least 10% above DT's actual overloading
            "V_upper_lim": 1.05,
            "V_lower_lim": 0.95,
            "Target_V": 1,
            "plot window open time": 1,  # seconds
            "Min PVLoad multiplier": 1,
            "Min Load multiplier": 0.1,
            "Max Load multiplier": 1,
            "max Regulators": 5,
            "Range B upper": 1.1,  # Range B limit inc
            "Range B lower": 0.20,
            "nominal_voltage": 120,
            "Max iterations": 20,
            "Create_upgrade_plots": True,
            "tps_to_test": [0.2, 2.2, 0.1, 2.0],# [min load multiplier without PV, max load multiplier without PV, min load multiplier with PV, max load multiplier with PV]
            "units key": ["mi", "kft", "km", "m", "Ft", "in", "cm"]  # Units key for lines taken from OpenDSS
        }
        for key,val in New_settings.items():
            if key not in self.Settings:
                self.Settings[key] = val
        # self.__dssinstance = dssInstance
        self.logger = Logger
        dss = dssInstance
        self.dssSolver = dssSolver
        # TODO: To be modified
        start_pen = self.Settings["DPV_penetration_HClimit"]
        target_pen = self.Settings["DPV_penetration_target"]
        pen_step = self.Settings["DPV_penetration_step"]
        self.pen_level = start_pen
        #self.compile_feeder_initialize()
        self.export_line_DT_parameters()
        self.pen_level = 0
        print("Determining thermal upgrades for PV penetration level: ", self.pen_level)
        start = time.time()
        self.dss_upgrades = [
            "//This file has all the upgrades determined using the control device placement algorithm \n"]
        # Determine available upgrades
        self.determine_available_line_upgrades()
        self.determine_available_xfmr_upgrades()

        # Determine initial loadings
        self.determine_line_ldgs()
        self.determine_xfmr_ldgs()
        num_elms_violated_curr_itr = len(self.xfmr_violations) + len(self.line_violations)
        print(num_elms_violated_curr_itr)
        # Store all initial violations to compare at the end of solution
        self.temp_line_viols = self.all_line_ldgs
        self.temp_xfmr_viols = self.all_xfmr_ldgs
        self.orig_line_ldg_lst = []
        self.orig_xfmr_ldg_lst = []
        self.equip_ldgs = {}
        self.equip_ldgs["Equipment_name"] = "Initial_loading"
        for key, vals in self.temp_line_viols.items():
            self.orig_line_ldg_lst.append(vals[0] * 100 / vals[1])
            self.equip_ldgs["Line_" + key] = (vals[0] * 100 / vals[1])
        for key, vals in self.temp_xfmr_viols.items():
            self.orig_xfmr_ldg_lst.append(vals[0] * 100 / vals[1])
            self.equip_ldgs["Xfmr_" + key] = (vals[0] * 100 / vals[1])
        self.write_to_json(self.equip_ldgs, "Initial_equipment_loadings_pen_{}".format(self.pen_level))

        # Mitigate thermal violations
        self.Line_trial_counter = 0
        while len(self.xfmr_violations) > 0 or len(self.line_violations) > 0:
            self.dssSolver.Solve()
            self.determine_line_ldgs()
            self.correct_line_violations()
            self.determine_xfmr_ldgs()
            self.correct_xfmr_violations()
            num_elms_violated_curr_itr = len(self.xfmr_violations) + len(self.line_violations)
            print("Iteration Count: ", self.Line_trial_counter)
            print("Number of devices with violations: ", num_elms_violated_curr_itr)
            self.Line_trial_counter += 1
            if self.Line_trial_counter > self.Settings["Max iterations"]:
                print("Max iterations limit reached, quitting")
                break
        self.determine_xfmr_ldgs()
        self.determine_line_ldgs()
        end = time.time()

        # Get final loadings
        self.final_line_ldg_lst = []
        self.final_xfmr_ldg_lst = []
        self.equip_ldgs = {}
        self.equip_ldgs["Equipment_name"] = "Final_loading"
        for key, vals in self.all_line_ldgs.items():
            self.final_line_ldg_lst.append(vals[0] * 100 / vals[1])
            self.equip_ldgs["Line_" + key] = (vals[0] * 100 / vals[1])
        for key, vals in self.all_xfmr_ldgs.items():
            self.final_xfmr_ldg_lst.append(vals[0] * 100 / vals[1])
            self.equip_ldgs["Xfmr_" + key] = (vals[0] * 100 / vals[1])
        self.write_to_json(self.equip_ldgs, "Final_equipment_loadings_pen_{}".format(self.pen_level))
        self.orig_line_ldg_lst.sort(reverse=True)
        self.final_line_ldg_lst.sort(reverse=True)
        self.orig_xfmr_ldg_lst.sort(reverse=True)
        self.final_xfmr_ldg_lst.sort(reverse=True)

        # Store final results
        print("Simulation Time:", end - start)
        print("After upgrades the solution converged: ", dss.Solution.Converged())
        print("Voltages after upgrades ", max(dss.Circuit.AllBusMagPu()), min(dss.Circuit.AllBusMagPu()))
        print("Substation power: ", dss.Circuit.TotalPower())
        plt.clf()
        plt.plot(self.orig_line_ldg_lst, "o", label="Starting Line Loadings")
        plt.plot(self.final_line_ldg_lst, "o", label="Ending Line Loadings")
        plt.plot(self.orig_xfmr_ldg_lst, "o", label="Starting Transformer Loadings")
        plt.plot(self.final_xfmr_ldg_lst, "o", label="Ending Transformer Loadings")
        plt.legend()
        plt.savefig(
            os.path.join(self.Settings["Outputs"], "Loading_comparisons_pen_{}".format(str(self.pen_level))),
            dpi=300)
        print("Writing Results to output file")
        self.write_dat_file()
        print("Processing upgrade results")

        # Process outputs
        input_dict = {
            "Feeder": self.Settings["Feeder"],
            "master file": self.Settings["master file"],
            "DPV_penetration_HClimit": self.Settings["DPV_penetration_HClimit"],
            "DPV_penetration_target": self.Settings["DPV_penetration_target"],
            "DPV_penetration_step": self.Settings["DPV_penetration_step"],
            "Outputs": self.Settings["Outputs"],
            "Create_plots": self.Settings["Create_upgrade_plots"]
        }

        postprocess_thermal_upgrades(input_dict, dss)
        return

    def export_line_DT_parameters(self):
        self.originial_line_parameters = {}
        self.originial_xfmr_parameters = {}
        dss.Lines.First()
        while True:
            ln_name = dss.Lines.Name()
            ln_lc = dss.Lines.LineCode()
            ln_len = dss.Lines.Length()
            len_units = self.Settings["units key"][dss.Lines.Units()-1]
            #len_units_alt = dss.Properties.Value("Units")
            ln_phases = dss.Lines.Phases()
            ln_b1 = dss.Lines.Bus1()
            ln_b2 = dss.Lines.Bus2()
            dss.Circuit.SetActiveBus(ln_b1)
            kv_b1 = dss.Bus.kVBase()
            dss.Circuit.SetActiveBus(ln_b2)
            kv_b2 = dss.Bus.kVBase()
            dss.Circuit.SetActiveElement("Line.{}".format(ln_name))
            if kv_b1!=kv_b2:
                print("To and from bus voltages ({} {}) do not match for line {}, quitting....".format(kv_b2, kv_b1, ln_name))
                quit()
            self.originial_line_parameters[ln_name] = {"linecode":ln_lc,"length": ln_len,
                                                       "num_phases": ln_phases,"line_kV": kv_b1,
                                                       "length_unit":len_units}
            if not dss.Lines.Next()>0:
                break
        self.write_to_json(self.originial_line_parameters, "Original_line_parameters")

        self.Linecodes_params = {}
        dss.LineCodes.First()
        while True:
            lc_name = dss.LineCodes.Name()
            ampacity = dss.LineCodes.NormAmps()
            self.Linecodes_params[lc_name] = {"Ampacity":ampacity}
            if not dss.LineCodes.Next()>0:
                break
        self.write_to_json(self.Linecodes_params, "Original_linecodes_parameters")

        dss.Transformers.First()
        while True:
            dt_name = dss.Transformers.Name()
            dt_phases = dss.Properties.Value("Phases")
            dt_numwdgs = dss.Transformers.NumWindings()
            dt_kva = []
            dt_conn = []
            dt_kv = []
            for wdgs in range(dt_numwdgs):
                dss.Transformers.Wdg(wdgs+1)
                dt_kva.append(float(dss.Properties.Value("kva")))
                dt_kv.append(float(dss.Properties.Value("kv")))
                dt_conn.append(dss.Properties.Value("conn"))
            self.originial_xfmr_parameters[dt_name] = {"num_phases":dt_phases,"num_windings": dt_numwdgs,
                                                       "wdg_kvas": dt_kva,"wdg_kvs": dt_kv,"wdg_conns": dt_conn}
            if not dss.Transformers.Next()>0:
                break
        self.write_to_json(self.originial_xfmr_parameters, "Original_xfmr_parameters")

    def process_DT_upgrades_file(self):
        self.compiled_xfmr_upgrades = {}
        f = open(os.path.join(self.Settings["Outputs"],"Originial_xfmr_parameters.json"), 'r')
        data = json.load(f)
        for xfmr,specs in data.items():
            par_xfmr_cnt = 0
            with open(os.path.join(self.Settings["Outputs"],"Thermal_upgrades.dss"), "r") as datafile:
                for line in datafile:
                    if line.startswith("New Transformer."):
                        params = line.split()
                        for param in params:
                            if param.startswith("Transformer."):
                                dt_name = param.split(".")[0]
                    elif line.startswith("Edit Transformer."):
                        print("")
        return

    def write_to_json(self, dict, file_name):
        with open(os.path.join(self.Settings["Outputs"],"{}.json".format(file_name)), "w") as fp:
            json.dump(dict, fp, indent=4)


    def write_dat_file(self):
        with open(os.path.join(self.Settings["Outputs"],"Thermal_upgrades_pen_{}.dss".format(str(self.pen_level))), "w") as datafile:
            for line in self.dss_upgrades:
                datafile.write(line)

    def determine_available_line_upgrades(self):
        self.avail_line_upgrades = {}
        dss.Lines.First()
        while True:
            line_name = dss.Lines.Name()
            line_code = dss.Lines.LineCode()
            phases = dss.Lines.Phases()
            # TODO change this to properties
            from_bus = dss.CktElement.BusNames()[0].split(".")[0]
            to_bus = dss.CktElement.BusNames()[1].split(".")[0]
            dss.Circuit.SetActiveBus(from_bus)
            kv_from_bus = dss.Bus.kVBase()
            dss.Circuit.SetActiveBus(to_bus)
            kv_to_bus = dss.Bus.kVBase()
            dss.Circuit.SetActiveElement("Line.{}".format(line_name))
            norm_amps = dss.Lines.NormAmps()
            if kv_from_bus!=kv_to_bus:
                print("For line {} the from and to bus kV ({} {}) do not match, quitting...".format(line_name,
                                                                                                    kv_from_bus,
                                                                                                    kv_to_bus))
                quit()
            key = "type_"+"{}_".format(phases)+"{}".format(round(kv_from_bus,3))
            if key not in self.avail_line_upgrades:
                self.avail_line_upgrades[key] = {"{}".format(line_code):[norm_amps]}
            elif key in self.avail_line_upgrades:
                for lc_key,lc_dict in self.avail_line_upgrades.items():
                    if line_code not in lc_dict:
                        self.avail_line_upgrades[key]["{}".format(line_code)]=[norm_amps]
            if not dss.Lines.Next()>0:
                break

    def determine_line_ldgs(self):
        self.line_violations = {}
        self.all_line_ldgs = {}
        self.solve_diff_tps_lines()
        for key,vals in self.line_violations_alltps.items():
            self.line_violations[key] = [max(vals[0]),vals[1]]
        for key, vals in self.all_line_ldgs_alltps.items():
            self.all_line_ldgs[key] = [max(vals[0]), vals[1]]

    def solve_diff_tps_lines(self):
        print(dss.PVsystems.Count())
        self.line_violations_alltps = {}
        self.all_line_ldgs_alltps = {}
        for tp_cnt in range(len(self.Settings["tps_to_test"])):
            # First two tps are for disabled PV case
            if tp_cnt==0 or tp_cnt==1:
                dss.run_command("BatchEdit PVSystem..* Enabled=False")
                dss.run_command("set LoadMult = {LM}".format(LM = self.Settings["tps_to_test"][tp_cnt]))
                self.dssSolver.Solve()
                print("tp count", tp_cnt)
                print(dss.Circuit.TotalPower())
            if tp_cnt==2 or tp_cnt==3:
                dss.run_command("BatchEdit PVSystem..* Enabled=True")
                dss.run_command("set LoadMult = {LM}".format(LM = self.Settings["tps_to_test"][tp_cnt]))
                self.dssSolver.Solve()
                print("tp count", tp_cnt)
                print(dss.Circuit.TotalPower())
            dss.Circuit.SetActiveClass("Line")
            dss.ActiveClass.First()
            while True:
                switch = dss.Properties.Value("switch")
                line_name = dss.CktElement.Name().split(".")[1].lower()
                line_limit = dss.CktElement.NormalAmps()
                raw_current = dss.CktElement.Currents()
                line_current = [math.sqrt(i ** 2 + j ** 2) for i, j in zip(raw_current[::2], raw_current[1::2])]
                ldg = round(max(line_current) / float(line_limit), 2)
                if switch == "False":
                    if line_name not in self.all_line_ldgs_alltps:
                        self.all_line_ldgs_alltps[line_name] = [[max(line_current)], line_limit]
                    elif line_name in self.all_line_ldgs_alltps:
                        self.all_line_ldgs_alltps[line_name][0].append(max(line_current))
                if ldg > self.Settings["line loading limit"] and switch == "False":  # and switch==False:
                    if line_name not in self.line_violations_alltps:
                        self.line_violations_alltps[line_name] = [[max(line_current)], line_limit]
                    elif line_name in self.line_violations_alltps:
                        self.line_violations_alltps[line_name][0].append(max(line_current))
                if not dss.ActiveClass.Next() > 0:
                    break
        return

    def correct_line_violations(self):
        # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
        # If a line code is not found or if line code is too overrated one or more parallel lines (num_par_lns-1)
        # may be added.

        if len(self.line_violations)>0:
            for key,vals in self.line_violations.items():
                dss.Circuit.SetActiveElement("Line.{}".format(key))
                phases = dss.Lines.Phases()
                length = dss.Lines.Length()
                units = self.Settings["units key"][dss.Lines.Units()-1]
                line_code = dss.Lines.LineCode()
                from_bus = dss.CktElement.BusNames()[0]
                to_bus = dss.CktElement.BusNames()[1]
                dss.Circuit.SetActiveBus(from_bus)
                kv_from_bus = dss.Bus.kVBase()
                dss.Circuit.SetActiveBus(to_bus)
                kv_to_bus = dss.Bus.kVBase()
                dss.Circuit.SetActiveElement("Line.{}".format(key))
                norm_amps = dss.Lines.NormAmps()
                num_par_lns = int(vals[0]*self.Settings["line_safety_margin"]/vals[1])+1
                if kv_from_bus != kv_to_bus:
                    print("For line {} the from and to bus kV ({} {}) do not match, quitting...".format(key,
                                                                                                        kv_from_bus,
                                                                                                        kv_to_bus))
                    quit()
                if float(norm_amps)-float(vals[1])>0.001:
                    print("For line {} the rated current values ({} {}) do not match, quitting...".format(key,
                                                                                                          norm_amps,
                                                                                                          vals[1]))
                    quit()
                lc_key = "type_"+"{}_".format(phases)+"{}".format(round(kv_from_bus,3))
                lcs_fnd_flag = 0
                if lc_key in self.avail_line_upgrades:
                    for lcs,lcs_vals in self.avail_line_upgrades[lc_key].items():
                        if lcs!=line_code:
                            if lcs_vals[0]>vals[0]*self.Settings["line_safety_margin"] and lcs_vals[0]<num_par_lns*norm_amps:
                                command_string = "Edit Line.{lnm} linecode={lnc}".format(lnm=key, lnc=lcs)
                                dss.run_command(command_string)
                                self.dssSolver.Solve()
                                self.write_dss_file(command_string)
                                lcs_fnd_flag = 1
                                break
                if lc_key not in self.avail_line_upgrades or lcs_fnd_flag==0:
                    # Add parallel lines since no suitable (correct ampacity/ratings or economical) line
                    # replacement was found
                    # print("{} Parallel lines required for line {}".format(num_par_lns-1, key))
                    for ln_cnt in range(num_par_lns-1):
                        command_string = "New Line.{lnm}_upgrade_{tr_cnt}_{cnt} bus1={b1} bus2={b2} length={lt} units={u}" \
                                         " linecode={lc} phases={ph} enabled=True".format(
                            lnm=key,
                            tr_cnt = self.Line_trial_counter,
                            cnt=ln_cnt,
                            b1=from_bus,
                            b2=to_bus,
                            lt=length,
                            u=units,
                            lc=line_code,
                            ph=phases
                        )
                        dss.run_command(command_string)
                        self.dssSolver.Solve()
                        self.write_dss_file(command_string)
        else:
            print("This DPV penetration has no line violations")
        return

    def determine_available_xfmr_upgrades(self):
        # If the kVA ratings for the windings do not match, the DT is not considered as a potential upgrade option.
        #  For this DT the upgrade will either be one or more DTs of its own ratings in parallel or a new DT with
        #  higher ratings but each winding will be of equal rating.
        # Get a unique id descriptive of DT number of phases, number of wdgs; wdg kvs and connections
        # Get essential DT characteristics: kVA, normal amps rating, %r for both windings to capture percent load loss,
        # and % noload loss
        self.avail_xfmr_upgrades = {}
        dss.Transformers.First()
        while True:
            ignore_upgrade=0
            xfmr_name = dss.Transformers.Name()
            # Figure out unique DT characteristics so possible upgrade options may be determined: key is: num phases;
            # num wdgs; kv and connection of each winding
            phases = dss.CktElement.NumPhases()
            num_wdgs = dss.Transformers.NumWindings()
            norm_amps = dss.CktElement.NormalAmps()
            conn_list = []
            wdg_kva_list = []
            wdg_kv_list = []
            per_R_list = []
            per_losses = []
            per_reac = []
            per_reac.append(dss.Properties.Value("xhl"))
            if num_wdgs==3:
                per_reac.append(dss.Properties.Value("xht"))
                per_reac.append(dss.Properties.Value("xlt"))
            for wdgs in range(num_wdgs):
                dss.Transformers.Wdg(wdgs+1)
                wdg_kva_list.append(float(dss.Properties.Value("kva")))
                wdg_kv_list.append(float(dss.Properties.Value("kv")))
                conn_list.append(dss.Properties.Value("conn"))
                per_R_list.append(dss.Properties.Value("%r"))
            per_losses.append(dss.Properties.Value("%noloadloss"))
            per_losses.append(dss.Properties.Value("%loadloss"))
            if per_losses[0]>per_losses[1]:
                print("For DT {}, %noloadloss is greater than %loadloss {}, continuing...".format(xfmr_name,
                                                                                                          per_losses))
            for i in wdg_kva_list:
                if i!=wdg_kva_list[0]:
                    print(" DT {} will not be considered as a upgrade option as the kVA values of its" \
                          " windings do not match {}".format(xfmr_name,wdg_kva_list))
                    ignore_upgrade = 1
                    break
            if ignore_upgrade==1:
                continue
            key = "type_"+"{}_".format(phases)+"{}_".format(num_wdgs)
            for kv_cnt in range(len(wdg_kv_list)):
                key = key + "{}_".format(wdg_kv_list[kv_cnt])
                key = key + "{}_".format(conn_list[kv_cnt])
            # Get relevant parameters for each potential upgrade option
            if key not in self.avail_xfmr_upgrades:
                self.avail_xfmr_upgrades[key] = {xfmr_name:[wdg_kva_list,[norm_amps],per_R_list,per_losses,per_reac]}
            elif key in self.avail_xfmr_upgrades:
                if xfmr_name not in self.avail_xfmr_upgrades[key]:
                    self.avail_xfmr_upgrades[key][xfmr_name] = [wdg_kva_list,[norm_amps],per_R_list,per_losses,per_reac]
            if not dss.Transformers.Next()>0:
                break
        return

    def determine_xfmr_ldgs(self):
        # TODO: LA100 team please correct the logic used for determining DT loadings. This is the same logic Nicolas
        # TODO: used for the SETO project. This may break down for some DT configurations such as 3 wdg transformers
        self.xfmr_violations = {}
        self.all_xfmr_ldgs = {}
        self.determine_xfmr_ldgs_alltps()
        for key,vals in self.xfmr_violations_alltps.items():
            self.xfmr_violations[key] = [max(vals[0]),vals[1]]
        for key,vals in self.all_xfmr_ldgs_alltps.items():
            self.all_xfmr_ldgs[key] = [max(vals[0]),vals[1]]

    def determine_xfmr_ldgs_alltps(self):
        self.xfmr_violations_alltps = {}
        self.all_xfmr_ldgs_alltps = {}
        for tp_cnt in range(len(self.Settings["tps_to_test"])):
            # First two tps are for disabled PV case
            if tp_cnt == 0 or tp_cnt == 1:
                dss.run_command("BatchEdit PVSystem..* Enabled=False")
                dss.run_command("set LoadMult = {LM}".format(LM=self.Settings["tps_to_test"][tp_cnt]))
                self.dssSolver.Solve()
                print("tp count", tp_cnt)
                print(dss.Circuit.TotalPower())
            if tp_cnt == 2 or tp_cnt == 3:
                dss.run_command("BatchEdit PVSystem..* Enabled=True")
                dss.run_command("set LoadMult = {LM}".format(LM=self.Settings["tps_to_test"][tp_cnt]))
                self.dssSolver.Solve()
                print("tp count", tp_cnt)
                print(dss.Circuit.TotalPower())
            dss.Transformers.First()
            while True:
                xfmr_name = dss.CktElement.Name().split(".")[1].lower()
                xfmr_limit = dss.CktElement.NormalAmps()
                # NOTE: Currents gives a vector of values:
                # [active_current_phase1_primary, reactive_current_phase1_primary,..., active_current_neutral_primary,
                #  reactive_current_neutral_primary, active_current_phase1_secondary,..., reactive_current_neutral_secondary]
                raw_current = dss.CktElement.Currents()
                # Compute the current from active and reactive
                xfmr_current = [math.sqrt(i ** 2 + j ** 2) for i, j in zip(raw_current[::2], raw_current[1::2])]
                # Clip the secondary values....
                xfmr_current = xfmr_current[:int(.5 * len(xfmr_current))]
                # Compute the loading
                ldg = round(max(xfmr_current) / float(xfmr_limit), 2)
                if xfmr_name not in self.all_xfmr_ldgs_alltps:
                    self.all_xfmr_ldgs_alltps[xfmr_name] = [[max(xfmr_current)], xfmr_limit]
                elif xfmr_name in self.all_xfmr_ldgs_alltps:
                    self.all_xfmr_ldgs_alltps[xfmr_name][0].append(max(xfmr_current))
                if ldg > self.Settings["DT loading limit"]:
                    if xfmr_name not in self.xfmr_violations_alltps:
                        self.xfmr_violations_alltps[xfmr_name] = [[max(xfmr_current)], xfmr_limit]
                    elif xfmr_name in self.xfmr_violations_alltps:
                        self.xfmr_violations_alltps[xfmr_name][0].append(max(xfmr_current))
                if not dss.Transformers.Next() > 0:
                    break

    def correct_xfmr_violations(self):
        # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
        # If a line code is not found or if line code is too overrated one or more parallel lines (num_par_lns-1)
        # may be added.

        if len(self.xfmr_violations)>0:
            for key,vals in self.xfmr_violations.items():
                # Determine which category this DT belongs to
                # dss.Circuit.SetActiveElement("Transformer.{}".format(key))
                dss.Transformers.Name(key)
                phases = dss.CktElement.NumPhases()
                num_wdgs = dss.Transformers.NumWindings()
                norm_amps = dss.CktElement.NormalAmps()
                conn_list = []
                wdg_kva_list = []
                wdg_kv_list = []
                per_R_list = []
                per_losses = []
                per_reac = []
                per_reac.append(dss.Properties.Value("xhl"))
                if num_wdgs == 3:
                    per_reac.append(dss.Properties.Value("xht"))
                    per_reac.append(dss.Properties.Value("xlt"))
                for wdgs in range(num_wdgs):
                    dss.Transformers.Wdg(wdgs + 1)
                    wdg_kva_list.append(float(dss.Properties.Value("kva")))
                    wdg_kv_list.append(float(dss.Properties.Value("kv")))
                    conn_list.append(dss.Properties.Value("conn"))
                    per_R_list.append(dss.Properties.Value("%r"))
                buses_list = dss.CktElement.BusNames()
                per_losses.append(dss.Properties.Value("%noloadloss"))
                # per_losses.append(dss.Properties.Value("%loadloss"))
                # if per_losses[0] > per_losses[1]:
                #     print("For DT {}, %noloadloss is greater than %loadloss {}, continuing...".format(key,
                #                                                                                       per_losses))
                if float(norm_amps)-float(vals[1])>0.001:
                    print("For DT {} the rated current values ({} {}) do not match, quitting...".format(key,
                                                                                                          norm_amps,
                                                                                                          vals[1]))
                    quit()
                num_par_dts = int(vals[0] * self.Settings["xfmr_safety_margin"] / vals[1]) + 1
                dt_key = "type_" + "{}_".format(phases) + "{}_".format(num_wdgs)
                for kv_cnt in range(len(wdg_kv_list)):
                    dt_key = dt_key + "{}_".format(wdg_kv_list[kv_cnt])
                    dt_key = dt_key + "{}_".format(conn_list[kv_cnt])
                # Find potential upgrades for this DT. This might be a new higher kVA rated DT in place of the original or
                #  one or more parallel DTs
                dt_fnd_flag = 0
                if dt_key in self.avail_xfmr_upgrades:
                    for dt,dt_vals in self.avail_xfmr_upgrades[dt_key].items():
                        if dt!=key:
                            if dt_vals[1][0]>vals[0]*self.Settings["xfmr_safety_margin"] and dt_vals[1][0]<num_par_dts*norm_amps:
                                command_string = "Edit Transformer.{xf} %noloadloss={nll} ".format(xf=key,
                                                                                                  nll=dt_vals[3][0])
                                for wdgs_cnt in range(num_wdgs):
                                    wdg_str = "wdg={wdg_cnt} kVA={wdg_kva} %r={wdg_r} ".format(wdg_cnt=str(wdgs_cnt+1),
                                                                                               wdg_kva = dt_vals[0][wdgs_cnt],
                                                                                               wdg_r = dt_vals[2][wdgs_cnt])
                                    command_string = command_string + wdg_str
                                if num_wdgs==3:
                                    per_reac_str = "XLT={xlt} XHT={xht} ".format(xlt=dt_vals[4][2],
                                                                                xht=dt_vals[4][1])
                                    command_string = command_string + per_reac_str
                                add_str = "XHL={xhl} ".format(xhl=dt_vals[4][0])
                                dss.run_command(command_string)
                                self.dssSolver.Solve()
                                self.write_dss_file(command_string)
                                dt_fnd_flag=1
                                break
                if dt_key not in self.avail_xfmr_upgrades or dt_fnd_flag==0:
                    # Add parallel DTs since no suitable (correct ratings or economical) DT
                    # replacement was found
                    for dt_cnt in range(num_par_dts-1):
                        command_string = "New Transformer.{dtn}_upgrade_{tr_cnt}_{cnt} phases={phs} windings={wdgs}" \
                                         " %noloadloss={nll} ".format(
                            dtn=key,
                            tr_cnt = self.Line_trial_counter,
                            cnt=dt_cnt,
                            phs=phases,
                            wdgs=num_wdgs,
                            nll=per_losses[0]
                        )

                        for wdgs_cnt in range(num_wdgs):
                            wdg_str = "wdg={numwdg} bus={bus_wdg} kv={wdgs_kv} kVA={wdgs_kva} %r={wdgs_r} ".format(
                                numwdg=str(wdgs_cnt+1),
                                bus_wdg=buses_list[wdgs_cnt],
                                wdgs_kv=wdg_kv_list[wdgs_cnt],
                                wdgs_kva = wdg_kva_list[wdgs_cnt],
                                wdgs_r=per_R_list[wdgs_cnt]
                            )
                            command_string=command_string + wdg_str
                        if num_wdgs == 3:
                            per_reac_str = "XLT={xlt} XHT={xht} ".format(xlt=per_reac[2],
                                                                         xht=per_reac[1])
                            command_string = command_string + per_reac_str
                        add_str = "XHL={xhl} enabled=True".format(xhl=per_reac[0])
                        command_string=command_string+add_str
                        dss.run_command(command_string)
                        self.dssSolver.Solve()
                        self.write_dss_file(command_string)
        else:
            print("This DPV penetration has no Transformer thermal violations")
        return

    def write_dss_file(self, device_command):
        self.dss_upgrades.append(device_command+"\n")
        return

    def redirect_dss_upgrades(self):
        # Get all available dss upgrades files
        self.thermal_upgrades_files = [f for f in os.listdir(self.Settings["Outputs"]) if f.startswith("Thermal_upgrades_pen")]
        if int(self.pen_level) > int(self.Settings["DPV_penetration_HClimit"]):
            prev_pen_level = self.pen_level - self.Settings["DPV_penetration_step"]
            expected_file_name = "Thermal_upgrades_pen_{}.dss".format(prev_pen_level)
            print(expected_file_name)
            if expected_file_name in self.thermal_upgrades_files:
                expected_file_path = os.path.join(self.Settings["Outputs"],expected_file_name)
                dss.run_command("Redirect {}".format(expected_file_path))
                # Also append all upgrades in the previous penetration level to the next level
                with open(os.path.join(self.Settings["Outputs"], "Thermal_upgrades_pen_{}.dss".format(prev_pen_level)),"r") as datafile:
                    for line in datafile:
                        self.dss_upgrades.append(line)
            elif expected_file_name not in self.thermal_upgrades_files:
                print("Previous upgrades file does not exist, some error is code execution, quitting")
                quit()

    def run(self, step, stepMax):
        """Induces and removes a fault as the simulation runs as per user defined settings. 
        """
        self.logger.info('Running thermal upgrade post process')


        #step-=1 # uncomment the line if the post process needs to rerun for the same point in time
        return step



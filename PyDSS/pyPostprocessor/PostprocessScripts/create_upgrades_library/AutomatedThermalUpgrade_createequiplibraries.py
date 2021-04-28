#**Authors:**
# Akshay Kumar Jain; Akshay.Jain@nrel.gov
from PyDSS.exceptions import InvalidParameter
import opendssdirect as dss
import logging
import time
import json
import os

# Functionality to read both linecodes and line geometries added
logger = logging.getLogger(__name__)

class create_upgrades_library():
    def __init__(self, Settings):
        start_t = time.time()
        self.Settings = Settings
        self.sol = dss.Solution
        self.avail_line_upgrades = {}
        self.avail_xfmr_upgrades = {}
        # TODO: This has to be changed to os listdir method
        #self.avail_folders = self.Settings["Test_folders"]
        self.avail_folders = [f for f in os.listdir(os.path.join(self.Settings["Feeder_path"]))]
        for self.folders in self.avail_folders:
            self.sub_folders = [f for f in os.listdir(os.path.join(self.Settings["Feeder_path"], self.folders))]
            self.del_folders = []
            for fold in self.sub_folders:
                fold_end = fold.split(".")[-1]
                fold_end = "." + fold_end
                if fold_end in self.Settings["file types"]:
                    self.del_folders.append(fold)
            for fold in self.del_folders:
                self.sub_folders.remove(fold)
            for self.sub_folder in self.sub_folders:
                self.feeders = [f for f in os.listdir(os.path.join(self.Settings["Feeder_path"],self.folders,self.sub_folder))]
                self.del_folders = []
                for files in self.feeders:
                    files_end = files.split(".")[-1]
                    files_end = "."+files_end
                    if files_end in self.Settings["file types"]:
                        self.del_folders.append(files)
                    dead_folds = files.split("(")[-1].split(")")[0]
                    if dead_folds==self.Settings["ignore folder"]:
                        self.del_folders.append(files)
                for del_folds in self.del_folders:
                    self.feeders.remove(del_folds)
                for self.feeder in self.feeders:
                    self.compile_feeder_initialize()
                    if self.break_flag==0:
                        self.determine_available_line_upgrades()
                        self.determine_available_xfmr_upgrades()
                    else:
                        continue
        end_t = time.time()
        logger.debug(end_t-start_t)
        self.write_to_json(self.avail_line_upgrades,"Line_upgrades_library")
        self.write_to_json(self.avail_xfmr_upgrades, "Transformer_upgrades_library")
        logger.debug("")

    def write_to_json(self, dict, file_name):
        with open("{}.json".format(file_name), "w") as fp:
            json.dump(dict, fp, indent=4)

    def compile_feeder_initialize(self):
        self.break_flag = 0
        dss.run_command("Clear")
        dss.Basic.ClearAll()
        Master_file = os.path.join(self.Settings["Feeder_path"],self.folders,self.sub_folder,self.feeder,"Master.dss")
        logger.debug(Master_file)
        if not os.path.exists(Master_file):
            logger.debug("error {} does not exist".format(Master_file))
            self.break_flag=1

        if self.break_flag==0:
            try:
                # Solve base no DPV case: If base no DPV is outside ANSI B limits abort
                command_string = "Redirect {master}".format(master=Master_file)
                # self.write_dss_file(command_string)
                k = dss.run_command(command_string)
                if len(k)>1:
                    self.break_flag=1
                command_string = "Solve mode=snap"
                # self.write_dss_file(command_string)
                dss.run_command(command_string)
                self.sol.Solve()
            except:
                self.break_flag==1
                logger.debug("here")


    def determine_available_line_upgrades(self):
        try:
            dss.Lines.First()
            while True:
                line_name = dss.Lines.Name()
                line_code = dss.Lines.LineCode()
                ln_geo = ''
                ln_config = "linecode"
                if line_code == '':
                    ln_geo = dss.Lines.Geometry()
                    ln_config = "geometry"
                    # TODO: Distinguish between overhead and underground cables, currently there is no way to distinguish using opendssdirect/pydss etc
                    # dss.Circuit.SetActiveClass("linegeometry")
                    # flag = dss.ActiveClass.First()
                    # while flag>0:
                    #     flag = dss.ActiveClass.Next()
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
                    raise InvalidParameter("For line {} the from and to bus kV ({} {}) do not match, quitting...".format(line_name,
                                                                                                        kv_from_bus,
                                                                                                        kv_to_bus))
                key = "type_" + "{}_".format(ln_config) + "{}_".format(phases) + "{}".format(round(kv_from_bus, 3))
                # Add linecodes
                if key not in self.avail_line_upgrades and ln_config=="linecode":
                    self.avail_line_upgrades[key] = {"{}".format(line_code):[norm_amps]}
                elif key in self.avail_line_upgrades and ln_config=="linecode":
                    for lc_key,lc_dict in self.avail_line_upgrades.items():
                        if line_code not in lc_dict:
                            self.avail_line_upgrades[key]["{}".format(line_code)]=[norm_amps]
                        elif line_code in lc_dict:
                            if lc_dict[line_code][0]!=norm_amps and (line_code+"_{}".format(str(norm_amps))) not in lc_dict:
                                self.avail_line_upgrades[key]["{}_{}".format(line_code,str(norm_amps))]=[norm_amps]
                # Add line geometries
                if key not in self.avail_line_upgrades and ln_config == "geometry":
                    self.avail_line_upgrades[key] = {"{}".format(ln_geo): [norm_amps]}
                elif key in self.avail_line_upgrades and ln_config == "geometry":
                    for lc_key, lc_dict in self.avail_line_upgrades.items():
                        if ln_geo not in lc_dict:
                            self.avail_line_upgrades[key]["{}".format(ln_geo)] = [norm_amps]
                        elif ln_geo in lc_dict:
                            if lc_dict[ln_geo][0] != norm_amps and (ln_geo + "_{}".format(str(norm_amps))) not in lc_dict:
                                self.avail_line_upgrades[key]["{}_{}".format(ln_geo, str(norm_amps))] = [norm_amps]
                if not dss.Lines.Next()>0:
                    break
        except:
            pass

    def determine_available_xfmr_upgrades(self):
        # If the kVA ratings for the windings do not match, the DT is not considered as a potential upgrade option.
        #  For this DT the upgrade will either be one or more DTs of its own ratings in parallel or a new DT with
        #  higher ratings but each winding will be of equal rating.
        # Get a unique id descriptive of DT number of phases, number of wdgs; wdg kvs and connections
        # Get essential DT characteristics: kVA, normal amps rating, %r for both windings to capture percent load loss,
        # and % noload loss
        try:
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
                    logger.debug("For DT {}, %noloadloss is greater than %loadloss {}, continuing...".format(xfmr_name,
                                                                                                              per_losses))
                for i in wdg_kva_list:
                    if i!=wdg_kva_list[0]:
                        logger.debug(" DT {} will not be considered as a upgrade option as the kVA values of its" \
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
                        add_flag=0
                        # Compare parameters to make sure they do not already exist - avoid duplicate
                        for xfmrs,params in self.avail_xfmr_upgrades[key].items():
                            # Check wdg kva parameters
                            if len(params[0])==len(wdg_kva_list):
                                for elem_cnt in range(len(wdg_kva_list)):
                                    if params[0][elem_cnt]!=wdg_kva_list[elem_cnt]:
                                        add_flag=1
                                        break
                            else:
                                add_flag = 1
                                break
                            # Check norm amps
                            if params[1][0]!=norm_amps:
                                add_flag = 1
                                break
                            # Check percentage R values
                            if len(params[2])==len(per_R_list):
                                for elem_cnt in range(len(per_R_list)):
                                    if float(params[2][elem_cnt])!=float(per_R_list[elem_cnt]):
                                        add_flag=1
                                        break
                            else:
                                add_flag = 1
                                break
                            # Check percentage losses
                            if len(params[3]) == len(per_losses):
                                for elem_cnt in range(len(per_losses)):
                                    if float(params[3][elem_cnt]) != float(per_losses[elem_cnt]):
                                        add_flag = 1
                                        break
                            else:
                                add_flag = 1
                                break
                            # Check percentage reactance values
                            if len(params[4]) == len(per_reac):
                                for elem_cnt in range(len(per_reac)):
                                    if float(params[4][elem_cnt]) != float(per_reac[elem_cnt]):
                                        add_flag = 1
                                        break
                            else:
                                add_flag = 1
                                break
                        if add_flag==1:
                            self.avail_xfmr_upgrades[key][xfmr_name] = [wdg_kva_list,[norm_amps],per_R_list,per_losses,per_reac]
                        else:
                            pass
                    if xfmr_name in self.avail_xfmr_upgrades[key]:
                        pass
                if not dss.Transformers.Next()>0:
                    break
        except:
            logger.debug("xfmr")
            pass
        return

if __name__ == "__main__":
    Settings = {
        "Feeder_path"   : r"C:\Documents_NREL\Grid_Cost_DER_PhaseII\Control_device_placement\inputs",
        "Test_folders"  : ["J", "B"],
        "file types"    : [".dss", ".txt", ".png"],
        "ignore folder" : "DEAD"
    }
    data = create_upgrades_library(Settings)

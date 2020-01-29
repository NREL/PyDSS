import os
import json

# TODO: Figure out correct time points on which to run this algorithm. How to we reach a target HC and how
# TODO: do we optimize it such that the most economical solution is reached. Eventually how do we move this
# TODO: to QSTS simulations

# TODO: Correct existing cap control settings, if caps exist but capcontrols are not available add those -
# TODO: focus only on regs to correct voltages - somehow keep track of which regs belong to which cluster -
# TODO: so after placement of all required regs figure out which regs settings may be changed to achieve a certain HC
# TODO: If there are under voltage violations after correcting cap banks - increase their turn ON voltage set point in
# TODO: 0.5V increments

# End point if lesser than 1% or fewer than 5 nodes have Range A violations

class postprocess_voltage_upgrades():
    def __init__(self, Settings):
        self.Settings           = Settings
        self.cap_upgrades       = {}
        self.reg_upgrades       = {}
        self.source_xfmr_buses  = []
        self.read_orig_upgrades()
        self.get_cap_upgrades()
        self.get_sub_LTC_upgrades()
        self.get_existing_inline_regctrl_upgrades()
        self.get_added_devices()
        if len(self.reg_upgrades)>0 and len(self.cap_processed_ops)>0:
            for key,vals in self.reg_upgrades.items():
                self.cap_processed_ops["Regctrl.{}".format(key)]=vals
        self.write_to_json(self.cap_processed_ops,"Processed_voltage_upgrades")

    def write_to_json(self, dict, file_name):
        with open(os.path.join(self.Settings["outputs"],"{}.json".format(file_name)), "w") as fp:
            json.dump(dict, fp, indent=4)

    def read_orig_upgrades(self):
        f = open(os.path.join(self.Settings["outputs"],"Initial_capacitors.json"),"r")
        self.orig_caps = json.load(f)
        f = open(os.path.join(self.Settings["outputs"], "Initial_regulators.json"), "r")
        self.orig_regs = json.load(f)

    def get_cap_upgrades(self):
        # If cap controller did not initially exist, a new controller must have been added, elif
        # controller existed but it was not voltage controlled then also a new controller will
        # have to be added even though it would appear as an edit in the opendss upgrades files.
        # Otherwise if controller existed and it was voltage controlled plus original ON and OFF
        # settings were not used (indicated by "original" flag), then settings were modified
        self.cap_processed_ops = {}
        for key,vals in self.orig_caps.items():
            ctrl_added = 1
            ctrl_type = "Voltage"
            if not key.startswith("capbank_noctrl"):
                # This implies this capbank had a capcontroller - now figure out
                # whether it was voltage controlled or not
                if vals["Control type"].lower().startswith("volt"):
                    ctrl_added  = 0
                    cap_name    = "Capacitor."+vals["cap_name"]
                    cap_kvar    = vals["cap kVAR"]
                    cap_kv      = vals["cap_kv"]
                    ctrl_name   = key
                    # Now figure out whether settings were changed or not and what
                    # the final settings are
                    with open(os.path.join(self.Settings["outputs"],
                                           "Voltage_upgrades.dss"), "r") as datafile:
                        for line in datafile:
                            line=line.split()
                            cap_ctrl_nm = ''
                            for params in line:
                                if params.lower().startswith("capcontrol"):
                                    cap_ctrl_nm = params.split(".")[1].lower()
                            if cap_ctrl_nm=='':
                                continue
                            if cap_ctrl_nm==key.lower():
                                for params in line:
                                    if params.lower().startswith("on"):
                                        cap_on = float(params.split("=")[1])
                                    if params.lower().startswith("off"):
                                        cap_off = float(params.split("=")[1])
                    if cap_on==float(vals["ON"]) and cap_off==float(vals["OFF"]):
                        cap_settings = 0
                    else:
                        cap_settings = 1
                else:
                    ctrl_added      = 1
                    cap_name        = "Capacitor."+vals["cap_name"]
                    cap_kvar        = vals["cap kVAR"]
                    cap_kv          = vals["cap_kv"]
                    cap_settings    = 1
                    ctrl_name       = key
                    # Now figure out what the final settings are
                    with open(os.path.join(self.Settings["outputs"],
                                           "Voltage_upgrades.dss"), "r") as datafile:
                        for line in datafile:
                            line = line.split()
                            cap_ctrl_nm = ''
                            for params in line:
                                if params.lower().startswith("capcontrol"):
                                    cap_ctrl_nm = params.split(".")[1].lower()
                            if cap_ctrl_nm=='':
                                continue
                            if cap_ctrl_nm == key.lower():
                                for params in line:
                                    if params.lower().startswith("on"):
                                        cap_on = float(params.split("=")[1])
                                    if params.lower().startswith("off"):
                                        cap_off = float(params.split("=")[1])
            else:
                ctrl_added      = 1
                cap_name        = "Capacitor."+vals["cap_name"]
                cap_kvar        = vals["cap kVAR"]
                cap_kv          = vals["cap_kv"]
                cap_settings    = 1
                ctrl_name       = "capctrl"+vals["cap_name"]
                # Now figure out what the final settings are
                with open(os.path.join(self.Settings["outputs"],
                                       "Voltage_upgrades.dss"), "r") as datafile:
                    for line in datafile:
                        line = line.split()
                        cap_ctrl_nm = ''
                        for params in line:
                            if params.lower().startswith("capcontrol"):
                                cap_ctrl_nm = params.split(".")[1].lower()
                        if cap_ctrl_nm == '':
                            continue
                        if cap_ctrl_nm == ctrl_name.lower():
                            for params in line:
                                if params.lower().startswith("on"):
                                    cap_on = float(params.split("=")[1])
                                if params.lower().startswith("off"):
                                    cap_off = float(params.split("=")[1])
            self.cap_processed_ops[cap_name] = {
                "New controller added"          : ctrl_added,
                "Controller settings modified"  : cap_settings,
                "Final Settings"                : {
                    "capctrl name"              : ctrl_name,
                    "cap kvar"                  : cap_kvar,
                    "cap kV"                    : cap_kv,
                    "ctrl type"                 : ctrl_type,
                    "ON setting (V)"            : cap_on,
                    "OFF setting (V)"           : cap_off
                }
            }

    def get_sub_LTC_upgrades(self):
        # Figure out whether substation LTC exists - if yes figure whether a reg ctrl existed on it -
        # if yes figure whether its settings were changed. If regctrl did not exist - go to upgrades file to
        # figure out whether a new reg ctrl was added (check for enabled property) and get final settings.
        # Else if no xfmr existed - will be taken care of in the get_added_devices() function
        if "orig_substation_xfmr" in self.orig_regs:
            xfmr_name       = self.orig_regs["orig_substation_xfmr"]["xfmr_name"]
            reg_added       = 1
            reg_settings    = 1
            sub_xfmr        = 1
            flag_enabled    = "true"
            xfmr_kva        = self.orig_regs["orig_substation_xfmr"]["xfmr kVA"]
            xfmr_kv         = self.orig_regs["orig_substation_xfmr"]["xfmr_kv"]
            new_xfmr        = 0
            # Figure out source buses
            self.source_xfmr_buses = self.orig_regs["orig_substation_xfmr"]["bus_names"]
            # Figure out whether reg ctrl(s) originally existed for sub xfmr
            ctrl_name = ''
            for key,vals in self.orig_regs.items():
                if vals["xfmr_name"].lower()==xfmr_name.lower() and key.lower()!="orig_substation_xfmr":
                    reg_added = 0
                    ctrl_name = key.lower()
                    orig_reg_vsp = float(vals["reg_vsp"])
                    orig_reg_band = float(vals["reg_band"])
            # If LTC reg ctrl existed find out its final settings:
            if ctrl_name!='':
                with open(os.path.join(self.Settings["outputs"],
                                       "Voltage_upgrades.dss"), "r") as datafile:
                    for line in datafile:
                        line = line.split()
                        reg_ctrl_nm = ''
                        for params in line:
                            if params.lower().startswith("regcontrol"):
                                reg_ctrl_nm = params.split(".")[1].lower()
                        if reg_ctrl_nm=='':
                            continue
                        if reg_ctrl_nm==ctrl_name.lower():
                            for params in line:
                                if params.lower().startswith("vreg"):
                                    reg_vsp = float(params.split("=")[1])
                                if params.lower().startswith("band"):
                                    reg_band = float(params.split("=")[1])
                                if params.lower().startswith("enabled"):
                                    flag_enabled = params.lower().split("=")[1]
                if flag_enabled == "true":
                    ctrl_enabled = 1
                else:
                    ctrl_enabled = 0
                if reg_vsp==orig_reg_vsp and reg_band==orig_reg_band:
                    reg_settings = 0
            # If LTC reg ctrl did not exist, find its name and final settings
            elif ctrl_name == '':
                with open(os.path.join(self.Settings["outputs"],
                                       "Voltage_upgrades.dss"), "r") as datafile:
                    # First find out name of the newly added reg ctrl
                    for line in datafile:
                        if line.lower().startswith("new regcontrol"):
                            line = line.split()
                            xfmr_nm = ''
                            for params in line:
                                if params.lower().startswith("transformer"):
                                    xfmr_nm = params.split("=")[1].lower()
                            if xfmr_nm=='':
                                continue
                            elif xfmr_nm==xfmr_name.lower():
                                for params in line:
                                    if params.lower().startswith("regcontrol"):
                                        ctrl_name=params.split(".")[1].lower()
                                    if params.lower().startswith("vreg"):
                                        reg_vsp = float(params.split("=")[1])
                                    if params.lower().startswith("band"):
                                        reg_band = float(params.split("=")[1])
                    # With the above logic, the new LTC regctrl should have been found if it was added - now figure
                            #  out its final settings and whether or not it was disabled
                    if not ctrl_name=='':
                        flag_enabled = "true"
                        for line in datafile:
                            line = line.split()
                            reg_ctrl_nm=''
                            for params in line:
                                if params.lower().startswith("regcontrol"):
                                    reg_ctrl_nm=params.lower().split(".")[1]
                            if reg_ctrl_nm=='':
                                continue
                            elif reg_ctrl_nm==ctrl_name.lower():
                                for params in line:
                                    if params.lower().startswith("vreg"):
                                        reg_vsp = float(params.split("=")[1])
                                    if params.lower().startswith("band"):
                                        reg_band = float(params.split("=")[1])
                                    if params.lower().startswith("enabled"):
                                        flag_enabled = params.lower().split("=")[1]
                        if flag_enabled=="true":
                            ctrl_enabled = 1
                        else:
                            ctrl_enabled = 0
            if flag_enabled=="true":
                self.reg_upgrades[ctrl_name]        = {
                    "New controller added"          : reg_added,
                    "Controller settings modified"  : reg_settings,
                    "New transformer added"         : new_xfmr,
                    "Substation LTC"                : sub_xfmr,
                    "Final settings"                :{
                        "Transformer name"          : xfmr_name,
                        "Transformer kVA"           : xfmr_kva,
                        "Transformer kV"            : xfmr_kv,
                        "Reg ctrl V set point"      : reg_vsp,
                        "Reg ctrl deadband"         : reg_band
                    }
                }

        return

    def get_existing_inline_regctrl_upgrades(self):
        for key,vals in self.orig_regs.items():
            if key.lower()!="orig_substation_xfmr" and key.lower() not in self.reg_upgrades:
                # If reg ctrl is not sub LTC and existed originally, find final settings and whether they were updated or
                # not. If there is a weird case where multiple reg control objects are controlling a single xfmr, they might
                #  not be properly captured
                ctrl_name           = key.lower()
                orig_reg_vsp        = float(vals["reg_vsp"])
                orig_reg_band       = float(vals["reg_band"])
                xfmr_kva            = vals["xfmr kVA"]
                xfmr_kv             = vals["xfmr_kv"]
                xfmr_name           = vals["xfmr_name"]
                reg_added           = 0
                reg_settings        = 1
                sub_xfmr            = 0
                new_xfmr            = 0
                # Now get final settings
                with open(os.path.join(self.Settings["outputs"],
                                       "Voltage_upgrades.dss"), "r") as datafile:
                    # First find out name of the newly added reg ctrl
                    for line in datafile:
                        line = line.split()
                        reg_ctrl_nm = ''
                        for params in line:
                            if params.lower().startswith("regcontrol"):
                                reg_ctrl_nm = params.lower().split(".")[1]
                        if reg_ctrl_nm == '':
                            continue
                        elif reg_ctrl_nm == ctrl_name.lower():
                            for params in line:
                                if params.lower().startswith("vreg"):
                                    reg_vsp = float(params.split("=")[1])
                                if params.lower().startswith("band"):
                                    reg_band = float(params.split("=")[1])
                if reg_vsp==orig_reg_vsp and reg_band==orig_reg_band:
                    reg_settings=0
                self.reg_upgrades[ctrl_name] = {
                    "New controller added"          : reg_added,
                    "Controller settings modified"  : reg_settings,
                    "New transformer added"         : new_xfmr,
                    "Substation LTC"                : sub_xfmr,
                    "Final settings"                : {
                        "Transformer name"          : xfmr_name,
                        "Transformer kVA"           : xfmr_kva,
                        "Transformer kV"            : xfmr_kv,
                        "Reg ctrl V set point"      : reg_vsp,
                        "Reg ctrl deadband"         : reg_band
                    }
                }
        return

    def get_added_devices(self):
        # First determine what all new reg control devices were added - so basically if regctrl is not in reg upgrades
        #  by this point - it implies that it is neither sub LTC reg ctrl and nor is it an existing reg ctrl device
        new_regctrl_list = []
        with open(os.path.join(self.Settings["outputs"],
                               "Voltage_upgrades.dss"), "r") as datafile:
            # First find out name of the newly added reg ctrl
            for n_line in datafile:
                n_line = n_line.split()
                reg_ctrl_nm = ''
                for params in n_line:
                    if params.lower().startswith("regcontrol"):
                        reg_ctrl_nm = params.lower().split(".")[1]
                if reg_ctrl_nm == '':
                    continue
                if reg_ctrl_nm not in self.reg_upgrades and reg_ctrl_nm not in new_regctrl_list:
                    new_regctrl_list.append(reg_ctrl_nm)
            # Now find out the new regctrl devices' xfmr name, xfmr ratings, set points etc
            if len(new_regctrl_list)>0:
                for ctrl_name in new_regctrl_list:
                    ctrl_node       = ctrl_name.split("new_regctrl_")[1].lower()
                    xfmr_name       = "new_xfmr_"+ctrl_node
                    reg_added       = 1
                    reg_settings    = 1
                    sub_xfmr        = 0
                    new_xfmr        = 1
                    # get xfmr parameters
                    with open(os.path.join(self.Settings["outputs"],
                                           "Voltage_upgrades.dss"), "r") as datafile:
                        for line in datafile:
                            line = line.split()
                            tmp_xfmr_name = ''
                            for params in line:
                                if params.lower().startswith("transformer."):
                                    tmp_xfmr_name=params.split(".")[1].lower()
                            if tmp_xfmr_name==xfmr_name:
                                with open(os.path.join(self.Settings["outputs"],
                                                       "Voltage_upgrades.dss"), "r") as datafile:
                                    for nline in datafile:
                                        nline = nline.split()
                                        for param in nline:
                                            if param.lower().startswith("kvs"):
                                                xfmr_kv = float(param.lower().split("=")[1].split("(")[1].split(",")[0])
                                            if param.lower().startswith("kvas"):
                                                xfmr_kva = float(param.lower().split("=")[1].split("(")[1].split(",")[0])
                    # Now get reg ctrl final settings
                    with open(os.path.join(self.Settings["outputs"],
                                           "Voltage_upgrades.dss"), "r") as datafile:
                        for line in datafile:
                            line = line.split()
                            reg_ctrl_nm = ''
                            for params in line:
                                if params.lower().startswith("regcontrol"):
                                    reg_ctrl_nm = params.lower().split(".")[1]
                            if reg_ctrl_nm == '':
                                continue
                            elif reg_ctrl_nm == ctrl_name.lower():
                                for params in line:
                                    if params.lower().startswith("vreg"):
                                        reg_vsp = float(params.split("=")[1])
                                    if params.lower().startswith("band"):
                                        reg_band = float(params.split("=")[1])
                    self.reg_upgrades[ctrl_name]        = {
                        "New controller added"          : reg_added,
                        "Controller settings modified"  : reg_settings,
                        "New transformer added"         : new_xfmr,
                        "Substation LTC"                : sub_xfmr,
                        "Final settings"                : {
                            "Transformer name"          : xfmr_name,
                            "Transformer kVA"           : xfmr_kva,
                            "Transformer kV"            : xfmr_kv,
                            "Reg ctrl V set point"      : reg_vsp,
                            "Reg ctrl deadband"         : reg_band
                        }
                        }
        return

if __name__ == "__main__":
    Settings = {
        "outputs"   : "../Outputs"
    # This number gives the maximum number of regulators placed in the feeder apart from substation LTC
    }
    data = postprocess_voltage_upgrades(Settings)
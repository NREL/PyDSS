#**Authors:**
# Akshay Kumar Jain; Akshay.Jain@nrel.gov

import os
import json
import logging

# TODO: do we optimize it such that the most economical solution is reached. Eventually how do we move this
# TODO: to QSTS simulations

# TODO: Correct existing cap control settings, if caps exist but capcontrols are not available add those -
# TODO: focus only on regs to correct voltages - somehow keep track of which regs belong to which cluster -
# TODO: so after placement of all required regs figure out which regs settings may be changed to achieve a certain HC
# TODO: If there are under voltage violations after correcting cap banks - increase their turn ON voltage set point in
# TODO: 0.5V increments

# End point if lesser than 1% or fewer than 5 nodes have Range A violations


# function to compare two dictionaries with same format
# only compares common elements present in both original and new dictionaries
def compare_dict(old, new):
    field_list = []
    change = {}
    sharedKeys = set(old.keys()).intersection(new.keys())
    for key in sharedKeys:
        change_flag = False
        for sub_field in old[key]:
            if old[key][sub_field] != new[key][sub_field]:
                change_flag = True
                field_list.append(sub_field)
        if change_flag:
            change[key] = field_list
    return change


class postprocess_voltage_upgrades():
    def __init__(self, Settings, logger):
        self.Settings = Settings
        self.logger = logger
        self.new_reg_controls = self.Settings["new_reg_controls"]
        self.orig_reg_controls = self.Settings["orig_reg_controls"]
        self.new_capacitors = self.Settings["new_capacitors"]
        self.orig_capacitors = self.Settings["orig_capacitors"]
        self.new_capcontrols = self.Settings["new_capcontrols"]
        self.orig_capcontrols = self.Settings["orig_capcontrols"]
        self.new_ckt_info = self.Settings["new_ckt_info"]
        # next line not used anywhere - new is used. This gave error when substation transformer
        # was added in voltage upgrades. didnt exist in original ckt info. TODO: need to check before removing
        self.orig_ckt_info = self.Settings["orig_ckt_info"]  # not used
        self.orig_xfmr_info = self.Settings["orig_xfmr_info"]
        self.final_cap_upgrades = {}
        self.final_reg_upgrades = {}
        self.processed_outputs = {}
        # TODO check - if new substation transformer is added in voltage upgrades code, is that cost considered here

        if self.new_capcontrols:
            self.get_capacitor_upgrades()
        if self.new_reg_controls:
            self.get_regulator_upgrades()

        self.processed_outputs["feederhead_name"] = self.Settings["feederhead_name"]
        self.processed_outputs["feederhead_basekV"] = self.Settings["feederhead_basekV"]
        self.write_to_json(self.processed_outputs, "Processed_voltage_upgrades")

    # function to get capacitor upgrades
    def get_capacitor_upgrades(self):
        # STEP 1: compare controllers that exist in both: original and new- and get difference
        change = compare_dict(self.orig_capcontrols, self.new_capcontrols)
        modified_capacitors = list(change.keys())
        # STEP 2: account for any new controllers added (which are not there in original)
        new_addition = list(set(self.new_capcontrols.keys()) -
                            (set(self.orig_capcontrols.keys()) & set(self.new_capcontrols.keys())))
        cap_upgrades = [*modified_capacitors, *new_addition]  # combining these two lists to get upgraded capacitors
        if cap_upgrades:
            for ctrl_name in cap_upgrades:
                self.final_cap_upgrades["ctrl_name"] = ctrl_name
                self.final_cap_upgrades["cap_name"] = "Capacitor." + self.new_capcontrols[ctrl_name]["cap_name"]
                self.final_cap_upgrades["cap_kvar"] = self.new_capcontrols[ctrl_name]["cap_kvar"]
                self.final_cap_upgrades["cap_kv"] = self.new_capcontrols[ctrl_name]["cap_kv"]
                self.final_cap_upgrades["cap_on"] = self.new_capcontrols[ctrl_name]["onsetting"]
                self.final_cap_upgrades["cap_off"] = self.new_capcontrols[ctrl_name]["offsetting"]
                self.final_cap_upgrades["ctrl_type"] = self.new_capcontrols[ctrl_name]["control_type"]
                self.final_cap_upgrades["cap_settings"] = 1
                # if there are differences between original and new controllers
                if ctrl_name in modified_capacitors:
                    # if control type in original controller is voltage, only settings are changed
                    if self.orig_capcontrols[ctrl_name]["control_type"].lower().startswith("volt"):
                        self.final_cap_upgrades["ctrl_added"] = 0
                    # if original controller type was current, new controller (voltage type) is said to be added
                    elif self.orig_capcontrols[ctrl_name]["control_type"].lower().startswith("current"):
                        self.final_cap_upgrades["ctrl_added"] = 1
                # if there are new controllers
                elif ctrl_name in new_addition:
                    self.final_cap_upgrades["ctrl_added"] = 1
            self.processed_outputs[self.final_cap_upgrades["cap_name"]] = {
                "New controller added": self.final_cap_upgrades["ctrl_added"],
                "Controller settings modified": self.final_cap_upgrades["cap_settings"],
                "Final Settings": {
                    "capctrl name": self.final_cap_upgrades["ctrl_name"],
                    "cap kvar": self.final_cap_upgrades["cap_kvar"],
                    "cap kV": self.final_cap_upgrades["cap_kv"],
                    "ctrl type": self.final_cap_upgrades["ctrl_type"],
                    "ON setting (V)": self.final_cap_upgrades["cap_on"],
                    "OFF setting (V)": self.final_cap_upgrades["cap_off"]
                }
            }

    # function to assign settings if regulator upgrades are on substation transformer
    def check_substation_LTC(self):
        if self.new_ckt_info["substation_xfmr"]["xfmr_name"].lower() == \
                self.final_reg_upgrades["xfmr_name"]:
            self.final_reg_upgrades["sub_xfmr"] = 1
            self.final_reg_upgrades["xfmr_kva"] = self.new_ckt_info["substation_xfmr"]["xfmr_kva"]
            self.final_reg_upgrades["xfmr_kv"] = self.new_ckt_info["substation_xfmr"]["xfmr_kv"]

    # function to check for regulator upgrades
    def get_regulator_upgrades(self):
        # STEP 1: compare controllers that exist in both: original and new
        change = compare_dict(self.orig_reg_controls, self.new_reg_controls)
        modified_regulators = list(change.keys())
        # STEP 2: account for any new controllers added (which are not there in original)
        new_addition = list(set(self.new_reg_controls.keys()) -
                            (set(self.orig_reg_controls.keys()) & set(self.new_reg_controls.keys())))
        reg_upgrades = [*modified_regulators, *new_addition]  # combining these two lists to get upgraded regulators
        # if there are any upgrades & enabled, only then write to the file
        if reg_upgrades:
            for ctrl_name in reg_upgrades:
                if self.new_reg_controls[ctrl_name]['enabled'][0] == True:
                    self.final_reg_upgrades["reg_settings"] = 1  # settings are changed
                    self.final_reg_upgrades["reg_ctrl_name"] = ctrl_name.lower()
                    self.final_reg_upgrades["reg_vsp"] = float(self.new_reg_controls[ctrl_name]["v_setpoint"][0])
                    self.final_reg_upgrades["reg_band"] = float(self.new_reg_controls[ctrl_name]["v_deadband"][0])
                    self.final_reg_upgrades["xfmr_kva"] = self.new_reg_controls[ctrl_name]["xfmr_kva"]
                    self.final_reg_upgrades["xfmr_kv"] = self.new_reg_controls[ctrl_name]["xfmr_kv"]
                    self.final_reg_upgrades["xfmr_name"] = self.new_reg_controls[ctrl_name]["xfmr_name"]
                    self.final_reg_upgrades["new_xfmr"] = 0  # default = new transformer is not added
                    self.final_reg_upgrades["sub_xfmr"] = 0  # default (is not substation xfmr)
                    # if regulators are modified (and exist in both original and new)
                    if ctrl_name in modified_regulators:
                        self.final_reg_upgrades["reg_added"] = 0  # not a new regulator
                        self.check_substation_LTC()  # check if regulator is on substation transformer
                    elif ctrl_name in new_addition:
                        self.final_reg_upgrades["reg_added"] = 1  # is a new regulator
                        self.check_substation_LTC()   # check if regulator is on substation transformer
                        # if regulator transformer is not in the original xfmr list, then a new xfmr
                        if self.final_reg_upgrades["xfmr_name"] not in self.orig_xfmr_info:
                            self.final_reg_upgrades["new_xfmr"] = 1  # is a new xfmr
                    self.processed_outputs["Regctrl." + self.final_reg_upgrades["reg_ctrl_name"]] = {
                        "New controller added": self.final_reg_upgrades["reg_added"],
                        "Controller settings modified": self.final_reg_upgrades["reg_settings"],
                        "New transformer added": self.final_reg_upgrades["new_xfmr"],
                        "Substation LTC": self.final_reg_upgrades["sub_xfmr"],
                        "Final settings": {
                            "Transformer name": self.final_reg_upgrades["xfmr_name"],
                            "Transformer kVA": self.final_reg_upgrades["xfmr_kva"],
                            "Transformer kV": self.final_reg_upgrades["xfmr_kv"],
                            "Reg ctrl V set point": self.final_reg_upgrades["reg_vsp"],
                            "Reg ctrl deadband": self.final_reg_upgrades["reg_band"]
                        }
                     }

    def write_to_json(self, dict, file_name):
        with open(os.path.join(self.Settings["outputs"],"{}.json".format(file_name)), "w") as fp:
            json.dump(dict, fp, indent=4)


if __name__ == "__main__":
    Settings = {
        "outputs": "../Outputs"
    }
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    data = postprocess_voltage_upgrades(Settings, logger)

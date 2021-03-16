from PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
from PyDSS.utils.utils import load_data
import requests
import json
import ast
import re
import os

class Utilidata_Interface(AbstractPostprocess):
    REQUIRED_INPUT_FIELDS_AND_DEFAULTS = {}
    IMPLEMENTATION_MODES = []

    def __init__(self, project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
        """Constructor method
        """
        super(Utilidata_Interface, self).__init__(
            project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger
        )
        configuration = load_data(inputs["config_file"])

        self.training_period = configuration['settings']['training period (hours)']
        self._uuid = configuration['settings']["uuid"]
        self.training_complete = False

        self.Settings = simulationSettings
        self.Objects = dssObjectsByClass
        self.Solver = dssSolver

        self.mAssets = self.get_measurement_assets(configuration['assets'])

        self.metadata = self.define_metadata()
        self.metadata["ts_data"] = {}
        self.Options = {**self.REQUIRED_INPUT_FIELDS_AND_DEFAULTS, **configuration}
        self.dssSolver = dssSolver
        self.dss = dssInstance
        self.Logger = Logger

        self.logger.info('Creating Utilidata interface')

    def define_constraints(self):
        metadata = {
            "metadata": {}
        }
        for elm_name, info in self.mAssets.items():
            constraints = self.get_constraint(elm_name, info['Controllable'])
            for i, ppty in enumerate(info['values']):
                values = info["result"][i]
                if isinstance(values, list):
                    for j, v in enumerate(values):
                        if constraints:
                            metadata["metadata"][f"{elm_name}___{ppty}___{j}"] = constraints
                else:
                    if constraints:
                        metadata["metadata"][f"{elm_name}___{ppty}"] = constraints
        return metadata

    def get_constraint(self, elm_name, isControllable):
        obj = self.mAssets[elm_name]['object']
        if obj._Class == "Capacitor":
            if isControllable:
                val = obj.GetParameter("NumSteps")
                return {"lower_bound": 0,"upper_bound": int(val)}
        elif obj._Class == "Load":
            if isControllable:
                val = obj.GetParameter("kW")
                return {"lower_bound": 0,"upper_bound": int(val)}
            pass
        elif obj._Class == "Transformer":
            if isControllable:
                val1 = obj.GetParameter("MinTap")
                val2 = obj.GetParameter("MaxTap")
                return {"lower_bound": val1,"upper_bound": val2}
        elif obj._Class == "Line":
            if isControllable:
                return {"direct_control": True}
            else:
                return {"direct_control": False}
        else:
            pass
        return None

    def define_metadata(self):
        metadata = {
            "metadata": {}
        }
        for elm_name, info in self.mAssets.items():
            for i, ppty in enumerate(info['values']):
                values = info["result"][i]
                if isinstance(values, list):
                    for j, v in enumerate(values):
                        metadata["metadata"][f"{elm_name}___{ppty}___{j}"] = {"meas_class": ppty}
                else:
                    metadata["metadata"][f"{elm_name}___{ppty}"] = {"meas_class": ppty}
        return metadata

    def get_measurements(self):
        timestamp = self.dssSolver.GetDateTime()
        meas = {}
        for name, info in self.metadata["metadata"].items():
            Data = name.split("___")
            if len(Data) == 3:
                elm_name, ppty, idx = Data
            else:
                elm_name, ppty = Data
                idx = None

            value = self.get_measurement(self.mAssets[elm_name]['object'], ppty)
            if isinstance(value, list):
                meas[name] = value[int(idx)]
            else:
                meas[name] = value
        return timestamp, meas

    def get_measurement(self, obj, ppty):
        res = None
        if ppty == "SWITCH_STATE":
            res = 1 if obj.GetValue("enabled") == "true" else 0
        elif ppty == "CAP_STATE":
            res = obj.GetParameter("States")
            res = ast.literal_eval(res)
        elif ppty == "AMI_V_120":
            res = obj.GetValue("VoltagesMagAng")
            vbase = obj.sBus[0].GetVariable("kVBase")
            res = [x for x in res if x != 0]
            res = [x / (1000.0 * vbase) * 120.0 for x in res if x != 0]
            res = res[::2]
            res = sum(res)/len(res)
        elif ppty == "AMI_P":
            res = obj.GetValue("Powers")
            res = sum(res[::2])
        elif ppty == "TAP_POSITION":
            res = obj.GetParameter("Tap")
        elif ppty == "SWING_V" or ppty == "PRIMARY_V":
            res = obj.GetValue("VoltagesMagAng")
            vbase = obj.sBus[1].GetVariable("kVBase")
            if len(obj.sBus) == 2:
                res = res[:int(len(res)/2)]
            res = [x/(1000.0 * vbase) * 120.0 for x in res if x != 0]
            res = res[::2]
        elif ppty == "SWING_P" or ppty == "PRIMARY_P":
            res = obj.GetValue("Powers")
            res = sum(res[::2])
        elif ppty == "SWING_Q" or ppty == "PRIMARY_Q":
            res = obj.GetValue("Powers")
            res = sum(res[1::2])
        return res

    def update_training_payload(self):
        time_stamp, results = self.get_measurements()
        self.metadata["ts_data"][str(time_stamp)] = results
        return

    def get_measurement_assets(self, asset_info):
        measured_elems = {}
        for class_name, info_list in asset_info.items():
            for info in info_list:
                if class_name != "Lines":
                    if info["measure"] == "all":
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            measured_elems[elm_name] = {
                                "object": elm_obj,
                                "values": info["values"],
                                "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                "Controllable": info["Controllable"]
                            }
                    elif info["measure"] == "from list":
                        for elem in info["list"]:
                            name = f"{class_name[:-1]}.{elem}"
                            if name in self.Objects[class_name]:
                                elm_obj = self.Objects[class_name][name]
                                measured_elems[name] = {
                                    "object": elm_obj,
                                    "values": info["values"],
                                    "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                    "Controllable": info["Controllable"]
                                }
                    elif info["measure"] == "use regex":
                        filt = info['regex']
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            if re.search(filt, elm_name):
                                measured_elems[elm_name] = {
                                    "object": elm_obj,
                                    "values": info["values"],
                                    "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                    "Controllable": info["Controllable"]
                                }
                else:
                    if info["measure"] == "all":
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            if elm_obj.GetValue("Switch") != "False":
                                measured_elems[elm_name] = {
                                    "object": elm_obj,
                                    "values": info["values"],
                                    "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                    "Controllable": info["Controllable"]
                                }
                    elif info["measure"] == "from list":
                        for elem in info["list"]:
                            name = f"{class_name[:-1]}.{elem}"
                            if name in self.Objects[class_name]:
                                if self.Objects[class_name][name].GetValue("Switch") != "False":
                                    elm_obj = self.Objects[class_name][name]
                                    measured_elems[name] = {
                                        "object": elm_obj,
                                        "values": info["values"],
                                        "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                        "Controllable": info["Controllable"]
                                    }
                    elif info["measure"] == "use regex":
                        filt = info['regex']
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            if re.search(filt, elm_name):
                                if elm_obj.GetValue("Switch") != "False":
                                    measured_elems[elm_name] = {
                                        "object": elm_obj,
                                        "values": info["values"],
                                        "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                        "Controllable": info["Controllable"]
                                    }
        return measured_elems

    def get_control_assets(self):
        return

    def submit_init_payload(self):
        json_object = json.dumps(self.metadata, indent=4)
        url = f"https://nrel.utilidatacloud.com/models/build/{self._uuid}"
        reply = requests.post(url, data=self.metadata, verify=False)
        print(json_object)
        print(reply.text)
        os.system("pause")
        return

    def submit_operation_payload(self):
        payload = self.define_constraints()
        time_stamp, results = self.get_measurements()
        payload[str(time_stamp)] = results
        json_object = json.dumps(payload, indent=4)
        print(json_object)
        os.system("pause")
        return


    def get_system_states(self):
        return

    def update_system_states(self):
        return

    def run(self, step, stepMax):
        tstep = self.Solver.GetStepSizeSec() / 3600.0
        if step * tstep < self.training_period:
            print("updating traning payload")
            self.update_training_payload()
        else:
            if not self.training_complete:
                self.submit_init_payload()
                self.training_complete = True
            else:
                self.submit_operation_payload()
        return step

    def _get_required_input_fields(self):
        return self.REQUIRED_INPUT_FIELDS_AND_DEFAULTS.keys()
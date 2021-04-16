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
        #print(dssObjects["Capacitor.cap_487254258"]._Variables)
        #quit()
        configuration = load_data(inputs["config_file"])
        rootPath = simulationSettings['Project']['Project Path']
        self.root_path = os.path.join(rootPath, simulationSettings['Project']['Active Project'])
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
                ntaps = obj.GetParameter("NumTaps") / 2
                return {"lower_bound": -ntaps,"upper_bound": ntaps}
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
            res = 1 if obj.GetParameter("enabled") == "true" else 0
        elif ppty == "CAP_STATE":
            res = obj.GetParameter("States")
            res = ast.literal_eval(res)
        elif ppty == "AMI_V_120":
            res = obj.GetVariable("VoltagesMagAng")
            vbase = obj.sBus[0].GetVariable("kVBase")
            res = [x for x in res if x != 0]
            res = [x / (1000.0 * vbase) * 120.0 for x in res if x != 0]
            res = res[::2]
            res = sum(res)/len(res)
        elif ppty == "AMI_P":
            res = obj.GetVariable("Powers")
            res = sum(res[::2])
        elif ppty == "TAP_POSITION":
            minTap = obj.GetParameter("MinTap")
            maxTap = obj.GetParameter("MaxTap")
            dV = maxTap - minTap
            ntaps = obj.GetParameter("NumTaps")
            dvdT = dV / ntaps
            tap = obj.GetParameter("Tap")
            tap_int = int(round((tap - 1) / dvdT))
            # print(tap, minTap, maxTap,dV, dvdT,tap_int)
            # quit()
            res = tap_int
        elif ppty == "SWING_V" or ppty == "PRIMARY_V":
            res = obj.GetVariable("VoltagesMagAng")
            vbase = obj.sBus[1].GetVariable("kVBase")
            if len(obj.sBus) == 2:
                res = res[:int(len(res)/2)]
            res = [x/(1000.0 * vbase) * 120.0 for x in res if x != 0]
            res = res[::2]
        elif ppty == "SWING_P" or ppty == "PRIMARY_P":
            res = obj.GetVariable("Powers")
            res = res[:int(len(res) / len(obj.sBus))]

            if ppty == "SWING_P":
                res = -sum(res[0::2])
            else:
                res = sum(res[0::2])

        elif ppty == "SWING_Q" or ppty == "PRIMARY_Q":
            res = obj.GetVariable("Powers")
            res = res[:int(len(res) / len(obj.sBus))]
            if ppty == "SWING_Q":
                res = -sum(res[1::2])
            else:
                res = sum(res[1::2])
        return res

    def update_training_payload(self):
        time_stamp, results = self.get_measurements()
        self.metadata["ts_data"][time_stamp.isoformat()] = results
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
        fpath = os.path.join(self.root_path, "init_payload.txt")
        with open(fpath, "w") as f:
            f.write(json_object)
        url = f"https://nrel.utilidatacloud.com/models/build/{self._uuid}"
        headers = {'Content-type': 'application/json'}
        reply = requests.post(url, data=json_object, verify=False, headers=headers)

        assert reply.status_code == 204
        self.disable_control_elements()
        return

    def submit_operation_payload(self):
        payload = {}
        payload["metadata"] = self.metadata["metadata"]
        time_stamp, results = self.get_measurements()
        payload["ts_data"] = {}
        payload["ts_data"][time_stamp.isoformat()] = results
        json_object = json.dumps(payload, indent=4)
        fpath = os.path.join(self.root_path, "oper_payload.txt")
        with open(fpath, "w") as f:
            f.write(json_object)
        url = f"https://nrel.utilidatacloud.com/optimize/{self._uuid}"
        headers = {'Content-type': 'application/json'}
        reply = requests.post(url, data=json_object, verify=False, headers=headers)
        if reply.status_code == 200:
            reply = reply.json()
            print(reply)
            return reply['recommendations']
        else:
            raise Exception(f"Error optimizing the model.\nReply from the server:\n{reply.text}")

    def disable_control_elements(self):
        reply = self._dssInstance.utils.run_command("Batchedit CapControl..* enabled=false")
        self.logger.info(f"Disabling local capacitor controls: {reply}")
        reply = self._dssInstance.utils.run_command("Batchedit RegControl..* enabled=false")
        self.logger.info(f"Disabling local regulator controls: {reply}")
        return

    def update_system_states(self, new_settings):
        for key, val in new_settings.items():
            Data = key.split("___")
            if len(Data) == 3:
                elm_name, ppty, idx = Data
            else:
                elm_name, ppty = Data
                idx = None

            if val['action']:
                obj = self.mAssets[elm_name]['object']
                if ppty == "CAP_STATE":
                    obj.SetParameter("Tap",)
                elif ppty == "TAP_POSITION":
                    minTap = obj.GetParameter("MinTap")
                    maxTap = obj.GetParameter("MaxTap")
                    dV = maxTap - minTap
                    ntaps = obj.GetParameter("NumTaps")
                    dvdT = dV / ntaps
                    tap = val['current_value'] + val['action']
                    res = 1 + tap * dvdT
                    reply = obj.SetParameter("Tap", res)
                    self.logger.info(f"Regulator {obj._Class}.{obj._Name} tap changed to {res}")
                else:
                    self.logger.warning(f"Please extend code to implement updates from the following key: {key}")
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
                new_settings = self.submit_operation_payload()
                self.update_system_states(new_settings)
        return step

    def _get_required_input_fields(self):
        return self.REQUIRED_INPUT_FIELDS_AND_DEFAULTS.keys()
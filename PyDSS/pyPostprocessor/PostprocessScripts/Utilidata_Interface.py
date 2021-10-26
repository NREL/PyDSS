from PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
from PyDSS.utils.utils import load_data
from datetime import timedelta
import opendssdirect as dss
import random as rdm
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
        rootPath = simulationSettings['Project']['Project Path']
        self.root_path = os.path.join(rootPath, simulationSettings['Project']['Active Project'])
        self.training_period = configuration['settings']['training period (hours)']
        self.retraining_period = configuration['settings']['retraining period (hours)']

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

        self.bufferSize = int(self.training_period * 3600 / dssSolver.GetStepSizeSec())
        self.day = self.dssSolver.GetDateTime().day

        self.firstBuildComplete = False

        choice = [1, 2, 5]
        ld = dss.Loads.First()
        while ld:
            dss.Loads.Model(rdm.choice(choice))
            ld = dss.Loads.Next()

        self.logger.info('Creating Utilidata interface')

    def define_constraints(self):
        metadata ={
            "metadata": {
                "air_temp": {
                    "meas_class": "WEATHER",
                    "device_id": "NOAA",
                    "feeder_id": "substation",
                },
                "solar_irradiance": {
                    "meas_class": "WEATHER",
                    "device_id": "NOAA",
                    "feeder_id": "substation"
                }
            }
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
                return {"lower_bound": 0, "upper_bound": int(val)}
        elif obj._Class == "Load":
            if isControllable:
                val = obj.GetParameter("kW")
                return {"lower_bound": 0, "upper_bound": int(val)}
        elif obj._Class == "Transformer":
            if isControllable:
                ntaps = obj.GetParameter("NumTaps") / 2
                return {"lower_bound": -ntaps, "upper_bound": ntaps}
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
            "metadata": {
                "air_temp": {
                    "meas_class": "WEATHER",
                    "device_id": "NOAA",
                    "feeder_id": "substation",
                },
                "solar_irradiance": {
                    "meas_class": "WEATHER",
                    "device_id": "NOAA",
                    "feeder_id": "substation"
                }
            }
        }
        for elm_name, info in self.mAssets.items():
            for i, ppty in enumerate(info['values']):
                values = info["result"][i]
                if isinstance(values, list):
                    for j, v in enumerate(values):
                        metadata["metadata"][f"{elm_name}___{ppty}___{j}"] = {
                            "meas_class": ppty,
                            "device_id": elm_name,
                            "feeder_id": info["feeder"]
                        }
                else:
                    metadata["metadata"][f"{elm_name}___{ppty}"] = {
                        "meas_class": ppty,
                        "device_id": elm_name,
                        "feeder_id":  info["feeder"]
                    }
        return metadata

    def get_measurements(self):
        timestamp = self.dssSolver.GetDateTime()
        meas = {}
        for name, info in self.metadata["metadata"].items():
            if name not in ["air_temp", "solar_irradiance"]:
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
            else:
                if name == "air_temp":
                    meas[name] = 35   #TODO get actual temp data here
                elif name == "solar_irradiance":
                    meas[name] = 2.4  #TODO get actual irradiance data here
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
        if len(self.metadata["ts_data"]) == self.bufferSize:
            tstamps = list(self.metadata["ts_data"].keys())
            del self.metadata["ts_data"][tstamps[0]]
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
                                "Controllable": info["Controllable"],
                                "feeder": self.get_feeder(elm_name)
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
                                    "Controllable": info["Controllable"],
                                    "feeder": self.get_feeder(name)
                                }
                    elif info["measure"] == "use regex":
                        filt = info['regex']
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            if re.search(filt, elm_name):
                                measured_elems[elm_name] = {
                                    "object": elm_obj,
                                    "values": info["values"],
                                    "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                    "Controllable": info["Controllable"],
                                    "feeder": self.get_feeder(elm_name)
                                }
                else:
                    if info["measure"] == "all":
                        for elm_name, elm_obj in self.Objects[class_name].items():
                            if elm_obj.GetValue("Switch") != "False":
                                measured_elems[elm_name] = {
                                    "object": elm_obj,
                                    "values": info["values"],
                                    "result": [self.get_measurement(elm_obj, x) for x in info["values"]],
                                    "Controllable": info["Controllable"],
                                    "feeder": self.get_feeder(elm_name)
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
                                        "Controllable": info["Controllable"],
                                        "feeder": self.get_feeder(name)
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
                                        "Controllable": info["Controllable"],
                                        "feeder": self.get_feeder(elm_name)
                                    }
        return measured_elems

    def find_filenames(self, path_to_dir, suffix=".csv"):
        filenames = os.listdir(path_to_dir)
        return [filename for filename in filenames if filename.endswith(suffix)]

    def get_feeder(self, elm_name):
        dss_path = os.path.join(
            str(self.Settings.project.active_project_path),
            "DSSfiles"
        )
        feeders = [x for x in os.listdir(dss_path) if os.path.isdir(os.path.join(dss_path, x))]
        for feeder in feeders:
            fpath = os.path.join(dss_path, feeder)
            files = self.find_filenames(fpath, suffix=".dss")
            for file in files:
                file_path = os.path.join(dss_path, feeder, file)
                with open(file_path) as f:
                    if elm_name.lower() in f.read().lower():
                        return feeder
        return "substation"

    def create_optimization_model(self):

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
            reply = reply.json()
            self.logger.error(f"Error optimizing the model.{reply['message']}")
            #raise Exception(f"Error optimizing the model.\nReply from the server:\n{reply.text}")

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
        self.update_training_payload()

        if not self.firstBuildComplete:
            if step * tstep % self.training_period == 0.0 and step is not 0:
                self.logger.info("Building initial optimization model")
                self.create_optimization_model()
                self.firstBuildComplete = True
        else:
            if step * tstep % self.retraining_period == 0.0 and step is not 0:
                self.logger.info("Rebuilding optimization model")
                self.create_optimization_model()
                self.training_complete = True
            else:
                if self.training_complete:
                    self.logger.info("Optimizing system state")
                    new_settings = self.submit_operation_payload()
                    if new_settings:
                        self.update_system_states(new_settings)
        return step

    def _get_required_input_fields(self):
        return self.REQUIRED_INPUT_FIELDS_AND_DEFAULTS.keys()

class NOAAData(object):
    def __init__(self, token):
        # NOAA API Endpoint
        self.url = 'https://www.ncdc.noaa.gov/cdo-web/api/v2/'
        self.h = dict(token=token)

    def poll_api(self, req_type, payload):
        # Initiate http request - kwargs are constructed into a dict and passed as optional parameters
        # Ex (limit=100, sortorder='desc', startdate='1970-10-03', etc)
        r = requests.get(self.url + req_type, headers=self.h, params=payload)

        if r.status_code != 200:  # Handle erroneous requests
            print("Error: " + str(r.status_code))
        else:
            r = r.json()
            try:
                return r['results']  # Most JSON results are nested under 'results' key
            except KeyError:
                return r  # for non-nested results, return the entire JSON string

    # Fetch available datasets
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#datasets
    def datasets(self, **kwargs):
        req_type = 'datasets'
        return self.poll_api(req_type, kwargs)

    # Fetch data categories
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#dataCategories
    def data_categories(self, **kwargs):
        req_type = 'datacategories'
        return self.poll_api(req_type, kwargs)

    # Fetch data types
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#dataTypes
    def data_types(self, **kwargs):
        req_type = 'datatypes'
        return self.poll_api(req_type, kwargs)

    # Fetch available location categories
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#locationCategories
    def location_categories(self, **kwargs):
        req_type = 'locationcategories'
        return self.poll_api(req_type, kwargs)

    # Fetch all available locations
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#locations
    def locations(self, **kwargs):
        req_type = 'locations'
        return self.poll_api(req_type, kwargs)

    # Fetch All available stations
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#stations
    def stations(self, h, p, **kwargs):
        req_type = 'stations'
        return self.poll_api(req_type, kwargs)

    # Fetch information about specific dataset
    def dataset_spec(self, set_code, **kwargs):
        req_type = 'datacategories/' + set_code
        return self.poll_api(req_type, kwargs)

    # Fetch data
    # http://www.ncdc.noaa.gov/cdo-web/webservices/v2#data
    def fetch_data(self, **kwargs):
        req_type = 'data'
        return self.poll_api(req_type, kwargs)

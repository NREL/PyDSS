import json
import os
from naerm_core.web.client_requests import send_sync_request
from http import HTTPStatus
import logging

class JSONwriter:
    def __init__(self, log_dir, bes_data_url, columnLength=None, notifier=None):
        self.log_dir = log_dir
        self.metadata = False
        self.payload = False
        self.bes_data_url = bes_data_url
        self.federate_close_url = f"{self.bes_data_url}/federate/close"
        self.asset_metadata_url = f"{self.bes_data_url}/federate/metadata"
        self.asset_timestep_url = f"{self.bes_data_url}/federate/timestep"
        self.notify = notifier
        return

    def parse_metadata(self, cName, LFresults, results):
        
        for k, v in LFresults[cName].items():
            data = k.split("__")
            name = data[0]
            if len(data) == 3:
                ppty = f"{data[1]}__{data[2]}"
            else:
                ppty = data[1]
            asset = self.check_asset(cName, None, results)
            if not asset:
                asset = {
                    "asset_type": cName,
                    "key_columns": ["Name"],
                    "key_values": [[name]],
                    "measurement_columns": [
                        {
                          "name": ppty,
                          "type": "numeric" if not isinstance(v, str) else "string",
                          "mappings": [{"key": "string", "value": "string"}]
                        }
                    ]
                }
                results["asset_data"].append(asset)
            else:
                if name not in asset["key_values"][0]:
                    asset["key_values"][0].append(name)
                colExists = False
                for cols in asset["measurement_columns"]:
                    if cols["name"] == ppty:
                        colExists = True
                if not colExists:
                    res = {
                        "name": ppty,
                        "type": "numeric" if not isinstance(v, str) else "string",
                        "mappings": [{"key": "string", "value": "string"}],
                    }
                    asset["measurement_columns"].append(res)
        return results

    def create_meta_data(self, LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime):
        results = {}
        results["cosim_uuid"] = cosim_uuid
        results["federate_uuid"] = fed_uuid
        results["interconnect"] = "distribution"
        results["asset_data"] = []
        for key in LFresults:
            results = self.parse_metadata(key, LFresults, results)
        return results

    def update_payload(self, timestep, fed_uuid, cosim_uuid):
        if not self.payload:
            self.payload = {
                "cosim_uuid": cosim_uuid,
                "federate_uuid": fed_uuid,
                "timesteps": [timestep]
            }
        else:
            self.payload["timesteps"].append(timestep)
        return

    def write(self, 
            fed_name, 
            currenttime, 
            LFresults, 
            index=None, 
            circuit=None, 
            fed_uuid=None, 
            cosim_uuid=None):

        if not self.metadata:
            self.metadata = self.create_meta_data(LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime)
            response = send_sync_request(self.asset_metadata_url, 'POST', body=self.metadata)
            if response.status != HTTPStatus.OK:
                msg = f'Unable to send asset metadata to Data API > ' \
                      f'{response.data.decode("utf-8")}'
                self.notify(msg, log_level=logging.ERROR)
        results = self.remap(LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime)
        asset_data = results.pop("asset_data")
        results.update({"assets": asset_data})
        response = send_sync_request(self.asset_timestep_url, 'POST',
                                         body=results)

        # If post request was not successful, log an error message
        if response.status != HTTPStatus.OK:
            msg = f'Unable to send asset timestep data to Data API at ' \
                    f'timestep {currenttime} > ' \
                    f'{response.data.decode("utf-8")}'
            self.notify(msg, log_level=logging.ERROR)
        if index != -1:
            self.update_payload(currenttime, fed_uuid, cosim_uuid)
        return

    def send_timesteps(self):
        response = send_sync_request(self.federate_close_url, 'POST',
                                     body=self.payload)

        # If post request was not successful, log an error message
        if response.status != HTTPStatus.OK:
            msg = f'Unable to send timestep data to Data API at cosim end > {response.data.decode("utf-8")}'
            self.notify(msg, log_level=logging.ERROR)



    def __del__(self):
        return

    def check_asset(self, className, ppty, results):
        for asset in results["asset_data"]:
            if ppty is not None:
                if "asset_type" in asset and asset["asset_type"] == className and ppty in asset:
                    return asset
            else:
                if "asset_type" in asset and asset["asset_type"] == className:
                    return asset
        return False

    def parse_class(self, cName, LFresults, results):
        for k, v in LFresults[cName].items():
            data = k.split("__")
            name = data[0]
            if len(data) == 3:
                ppty = f"{data[1]}__{data[2]}"
            else:
                ppty = data[1]
            asset = self.check_asset(cName, ppty, results)
            if not asset:
                asset = {
                    "asset_type": cName,
                    ppty: [v]
                }
                results["asset_data"].append(asset)
            else:
                asset[ppty].append(v)
        return results

    def remap(self, LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime):
        results = {}
        results["cosim_uuid"] = cosim_uuid
        results["federate_uuid"] = fed_uuid
        results["timestep"] = currenttime
        results["asset_data"] = []
        for key in LFresults:
            results = self.parse_class(key, LFresults, results)
        return results
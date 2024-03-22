import json
import os

class JSONwriter:
    def __init__(self, log_dir, columnLength=None):
        self.log_dir = log_dir
        self.metadata = False
        self.payload = False
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
                    "assetType": cName,
                    "keyColumns": "Name",
                    "keyValues": [name],
                    "measurementColumns": [
                        {
                          "name": ppty,
                          "type": "numeric" if not isinstance(v, str) else "string",
                          "mappings": {}
                        }
                    ]
                }
                results["assets"].append(asset)
            else:
                if name not in asset["keyValues"]:
                    asset["keyValues"].append(name)
                colExists = False
                for cols in asset["measurementColumns"]:
                    if cols["name"] == ppty:
                        colExists = True
                if not colExists:
                    res = {
                        "name": ppty,
                        "type": "numeric" if not isinstance(v, str) else "string",
                        "mappings": {},
                    }
                    asset["measurementColumns"].append(res)
        return results

    def create_meta_data(self, LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime):
        results = {}
        results["cosimUUID"] = cosim_uuid
        results["federateUUID"] = fed_uuid
        results["interconnect"] = "distribution"
        results["assets"] = []
        for key in LFresults:
            results = self.parse_metadata(key, LFresults, results)
        return results

    def update_payload(self, timestep, fed_uuid, cosim_uuid):
        if not self.payload:
            self.payload = {
                "cosimUUID": cosim_uuid,
                "federateUUID": fed_uuid,
                "timeSteps": [timestep]
            }
        else:
            self.payload["timeSteps"].append(timestep)
        return

    def write(self, fed_name, currenttime, LFresults, index=None, circuit=None, fed_uuid=None, cosim_uuid=None):
        jFile = open(os.path.join(self.log_dir, f"Results_{int(currenttime)}.json"), "w")
        pFile = open(os.path.join(self.log_dir, f"payload.json"), "w")
        if not self.metadata:
            mFile = open(os.path.join(self.log_dir, f"metadata.json"), "w")
            self.metadata = self.create_meta_data(LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime)
            json.dump(self.metadata, mFile, indent=4, sort_keys=True)
            mFile.close()
        results = self.remap(LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime)
        self.update_payload(currenttime, fed_uuid, cosim_uuid)
        json.dump(results, jFile, indent=4, sort_keys=True)
        json.dump(self.payload, pFile, indent=4, sort_keys=True)
        jFile.close()
        pFile.close()
        return

    def __del__(self):
        return

    def check_asset(self, className, ppty, results):
        for asset in results["assets"]:
            if ppty is not None:
                if "assetType" in asset and asset["assetType"] == className and ppty in asset:
                    return asset
            else:
                if "assetType" in asset and asset["assetType"] == className:
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
                    "assetType": cName,
                    ppty: [v]
                }
                results["assets"].append(asset)
            else:
                asset[ppty].append(v)
        return results

    def remap(self, LFresults, fed_name, fed_uuid, cosim_uuid, circuit, currenttime):
        results = {}
        results["cosimUUID"] = cosim_uuid
        results["federateUUID"] = fed_uuid
        results["timeStep"] = currenttime
        results["assets"] = []
        for key in LFresults:
            results = self.parse_class(key, LFresults, results)
        return results
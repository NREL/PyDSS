from pydss.ProfileManager.base_definitions import BaseProfileManager, BaseProfile
from pydss.ProfileManager.common import PROFILE_TYPES
from pydss.exceptions import InvalidParameter
from pydss.common import DATE_FORMAT
from datetime import datetime
import pandas as pd
import numpy as np
import datetime
import h5py
import copy
import os

class ProfileManager(BaseProfileManager):

    def __init__(self,  sim_instance, solver, options, logger, **kwargs):
        super(ProfileManager, self).__init__(sim_instance, solver, options, logger, **kwargs)
        self.Objects = kwargs["objects"]
        if os.path.exists(self.basepath):
            self.logger.info("Loading existing h5 store")
            self.store = h5py.File(self.basepath, "r+")
        else:
            self.logger.info("Creating new h5 store")
            self.store = h5py.File(self.basepath, "w")
            for profileGroup in PROFILE_TYPES.names():
                self.store.create_group(profileGroup)
        self.setup_profiles()
        return

    def setup_profiles(self):
        self.Profiles = {}
        for group, profileMap in self.mapping.items():
            if group in self.store:
                grp = self.store[group]
                for profileName, mappingDict in profileMap.items():
                    if profileName in grp:
                        objects = {x['object']: self.Objects[x['object']] for x in mappingDict}
                        self.Profiles[f"{group}/{profileName}"] = Profile(
                            self.sim_instance,
                            grp[profileName],
                            objects,
                            self.solver,
                            mappingDict,
                            self.logger,
                            **self.kwargs
                        )
                    else:
                        self.logger.warning("Group {} / data set {} not found in the h5 store".format(
                            group, profileName
                        ))
            else:
                self.logger.warning("Group {} not found in the h5 store".format(group))
        return

    def create_dataset(self, dname, pType, data ,startTime, resolution, units, info):
        grp = self.store[pType]
        if dname not in grp:
            dset = grp.create_dataset(
                dname,
                data=data,
                shape=(len(data),),
                maxshape=(None,),
                chunks=True,
                compression="gzip",
                compression_opts=4,
                shuffle=True
            )
            self.createMetadata(
                dset, startTime, resolution, data, units, info
            )
        else:
            self.logger.error('Dataset "{}" already exists in group "{}".'.format(dname, pType))
            raise Exception('Dataset "{}" already exists in group "{}".'.format(dname, pType))

    def add_from_arrays(self, data, name, pType, startTime, resolution, units="", info=""):
        r, c = data.shape
        if r > c:
            for i in range(c):
                d = data[:, i]
                dname = name if i==0 else "{}_{}".format(name, i)
                self.create_dataset(dname=dname, pType=pType, data=d, startTime=startTime, resolution=resolution,
                                    units=units, info=info)
        else:
            for i in range(r):
                d = data[i, :]
                dname = name if i==0 else "{}_{}".format(name, i)
                self.create_dataset(dname=dname, pType=pType, data=d, startTime=startTime, resolution=resolution,
                                    units=units, info=info)
        return

    def add_profiles_from_csv(self, csv_file, name, pType, startTime, resolution_sec=900, units="",
                              info=""):
        data = pd.read_csv(csv_file).values
        self.add_profiles(data, name, pType, startTime, resolution_sec=resolution_sec, units=units, info=info)


    def add_profiles(self, data, name, pType, startTime, resolution_sec=900, units="", info=""):
        if type(startTime) is not datetime.datetime:
            raise InvalidParameter("startTime should be a python datetime object")
        if pType not in PROFILE_TYPES.names():
            raise InvalidParameter("Valid values for pType are {}".format(PROFILE_TYPES.names()))
        if data:
            self.add_from_arrays(data, name, pType, startTime, resolution_sec, units=units, info=info)
        self.store.flush()
        return

    def createMetadata(self, dSet, startTime, resolution, data, units, info):
        metadata = {
            "sTime": str(startTime),
            "eTime": str(startTime + datetime.timedelta(seconds=resolution*len(data))),
            "resTime": resolution,
            "npts": len(data),
            "min": min(data),
            "max": max(data),
            "mean": np.mean(data),
            "units": units,
            "info": info,
        }
        for key, value in metadata.items():
            if isinstance(value, str):
                value = np.string_(value)
            dSet.attrs[key] = value
        return

    def remove_profile(self, profile_type, profile_name):
        return

    def update(self):
        results = {}
        for profileaName, profileObj in self.Profiles.items():
            result = profileObj.update()
            results[profileaName] = result
        return results

class Profile(BaseProfile):

    DEFAULT_SETTINGS = {
        "multiplier": 1,
        "normalize": False,
        "interpolate": False
    }

    def __init__(self, sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs):
        super(Profile, self).__init__(sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs)
        self.valueSettings = {x['object']: {**self.DEFAULT_SETTINGS, **x} for x in mapping_dict}

        self.bufferSize = kwargs["bufferSize"]
        self.buffer = np.zeros(self.bufferSize)
        self.profile = dataset
        self.neglectYear = kwargs["neglectYear"]
        self.Objects = devices

        self.attrs = self.profile.attrs
        self.sTime = datetime.datetime.strptime(self.attrs["sTime"].decode(), DATE_FORMAT)
        self.eTime = datetime.datetime.strptime(self.attrs["eTime"].decode(), '%Y-%m-%d %H:%M:%S.%f')
        self.simRes = solver.GetStepSizeSec()
        self.Time = copy.deepcopy(solver.GetDateTime())
        return

    def update_profile_settings(self):
        return

    def update(self, updateObjectProperties=True):
        self.Time = copy.deepcopy(self.solver.GetDateTime())
        if self.Time < self.sTime or self.Time > self.eTime:
            value = 0
            value1 = 0
        else:
            dT = (self.Time - self.sTime).total_seconds()
            n = int(dT / self.attrs["resTime"])
            value = self.profile[n]
            dT2 = (self.Time - (self.sTime + datetime.timedelta(seconds=int(n * self.attrs["resTime"])))).total_seconds()
            value1 = self.profile[n] + (self.profile[n+1] - self.profile[n]) * dT2 / self.attrs["resTime"]
        if updateObjectProperties:
            for objName, obj in self.Objects.items():
                if self.valueSettings[objName]['interpolate']:
                    value = value1
                mult = self.valueSettings[objName]['multiplier']
                if self.valueSettings[objName]['normalize']:
                    valueF = value / self.attrs["max"] * mult
                else:
                    valueF = value * mult
                obj.SetParameter(self.attrs["units"].decode(), valueF)
        return value



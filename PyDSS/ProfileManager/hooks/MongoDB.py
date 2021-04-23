from PyDSS.ProfileManager.base_definations import BaseProfileManager, BaseProfile
from bson.objectid import ObjectId
from pymongo import MongoClient

import json
from PyDSS.ProfileManager.common import PROFILE_TYPES
from PyDSS.exceptions import InvalidParameter
from PyDSS.common import DATE_FORMAT
from datetime import datetime
import pandas as pd
import numpy as np
import datetime
import copy
import os

class ProfileManager(BaseProfileManager):

    def __init__(self,  sim_instance, solver, options, logger, **kwargs):
        super(ProfileManager, self).__init__(sim_instance, solver, options, logger, **kwargs)
        self.Objects = kwargs["objects"]
        usersettings = options["Profiles"]['settings']

        self.client = MongoClient(self.basepath, username=usersettings["username"], password=usersettings["password"])
        self.db = self.client[usersettings["database"]]
        self.collections = self.db.collection_names()

        #self.one_Time_fix()
        self.setup_profiles()
        #quit()
        pass

    def one_Time_fix(self):
        C = self.db["Load"]
        cursor = C.find({"name": "customer_metadata"})
        customer_metadata = cursor.next()
        i = 0
        total_xfmr_load = {}
        for customerID, customerInfo in customer_metadata.items():
            if isinstance(customerInfo, dict):
                agg_load = customerInfo['section_id']
                if agg_load not in total_xfmr_load:
                    total_xfmr_load[agg_load] = []
                total_xfmr_load[agg_load].append(customerID)

        record = C.find({"date": {"$exists" : 1}})
        count = record.count()
        posts = []
        self.logger.debug("Count: ", count)
        for i in range(count):
            total_load = {}
            profile_data = record.next()
            self.logger.debug(profile_data["date"])
            time = profile_data["date"]
            total_load["_id"] = ObjectId()
            total_load["date"] = time
            total_load["aggregated"] = True
            vars = ["kw", "kvar"]
            for var in vars:
                if var not in total_load:
                    total_load[var] = {}
                for load_name, loadlist in total_xfmr_load.items():
                    if load_name not in total_load[var]:
                        total_load[var][load_name] = 0
                    for elm, val in profile_data[var].items():
                        if elm in loadlist:
                            total_load[var][load_name] += val
            posts.append(total_load)
            C.insert(total_load)
        self.logger.debug("Insert successful")


    def setup_profiles(self):
        for collection in self.collections:
            C = self.db[collection]
            record = C.find({"aggregated": {"$exists" : 1}})
            profile_data = record.next()
            profile_data.pop('_id', None)
            profile_data.pop('date', None)

            for property, obj_info in profile_data.items():
                if isinstance(obj_info, dict):
                    profile_dict = {}
                    for profile_name in obj_info:
                        if profile_name not in profile_dict:
                            profile_dict[profile_name] = []
                        model_found = False
                        for model_name, model in self.Objects.items():
                            if collection in model_name and profile_name in model_name:
                                profile_dict[profile_name].append(model_name)
                                model_found = True
                                break
                        if not model_found:
                            self.logger.warning(f"Profile {profile_name} could not be mapped to any element of type {collection} in the OpenDSS model")
                    for profile_name, model_list in profile_dict.items():
                        self.Profiles[f"{collection}.{profile_name}.{property}"] = Profile(
                                        self.sim_instance,
                                        (collection, profile_name, property),
                                        [self.Objects[x] for x in model_list],
                                        self.solver,
                                        None,
                                        self.logger,
                                        **self.kwargs
                                    )

        pass

    def update(self):
        self.logger.debug(self.solver.GetDateTime())
        for collection in self.collections:
            C = self.db[collection]
            record = C.find({"aggregated": {"$exists": 1}, 'date': self.solver.GetDateTime()})
            if not record.count():
                self.logger.warning(f"No record found for time period {self.solver.GetDateTime()} in the database")
            else:
                profile_data = record.next()
                profile_data.pop('_id', None)
                profile_data.pop('date', None)
                for profile in self.Profiles:
                    self.Profiles[profile].update(profile_data)



        pass

class Profile(BaseProfile):

    DEFAULT_SETTINGS = {
        "multiplier": 1,
        "normalize": False,
        "interpolate": False
    }

    def __init__(self, sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs):
        super(Profile, self).__init__(sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs)
        self.class_name, self.profile_name, self.property = self.dataset
        pass

    def update_profile_settings(self):
        pass

    def update(self, updateObjectProperties=True):
        data = updateObjectProperties
        value = data[self.property][self.profile_name]
        for device in self.devices:
            device.SetParameter(self.property, value)

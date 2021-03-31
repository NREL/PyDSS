from PyDSS.ProfileManager.base_definations import BaseProfileManager, BaseProfile
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
        pass

    def setup_profiles(self):
        pass

    def update(self):
        pass

class Profile(BaseProfile):

    DEFAULT_SETTINGS = {
        "multiplier": 1,
        "normalize": False,
        "interpolate": False
    }

    def __init__(self, sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs):
        super(Profile, self).__init__(sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs)
        pass

    def update_profile_settings(self):
        pass

    def update(self, updateObjectProperties=True):
        pass


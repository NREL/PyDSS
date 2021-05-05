from PyDSS.common import PROFILE_MAPPING
import datetime
import toml
import abc
import os


class BaseProfileManager(abc.ABC):
    def __init__(self, sim_instance, solver, options, logger, **kwargs):
        self.sim_instance = sim_instance
        self.options = options
        self.solver = solver
        self.logger = logger
        self.kwargs = kwargs
        if not options["Profiles"]["is_relative_path"]:
            self.basepath = options["Profiles"]["source"]
        else:
            self.basepath = os.path.join(
                options["Project"]["Project Path"],
                options["Project"]["Active Project"],
                "Profiles",
                options["Profiles"]["source"],
            )
        self.mapping_file = os.path.join(
            options["Project"]["Project Path"],
            options["Project"]["Active Project"],
            "Profiles",
            PROFILE_MAPPING
        )
        self.Profiles = {}
        self.mapping = toml.load(open(self.mapping_file , "r"))
        self.sTime = None
        self.eTime = None
        self.simRes = None

    @abc.abstractmethod
    def setup_profiles(self):
        pass

    @abc.abstractmethod
    def update(self):
        pass


class BaseProfile(abc.ABC):
    def __init__(self, sim_instance, dataset, devices, solver, mapping_dict, logger, **kwargs):
        self.sim_instance = sim_instance
        self.mapping_dict = mapping_dict
        self.dataset = dataset
        self.devices = devices
        self.logger = logger
        self.solver = solver

    @abc.abstractmethod
    def update_profile_settings(self):
        pass

    @abc.abstractmethod
    def update(self):
        pass

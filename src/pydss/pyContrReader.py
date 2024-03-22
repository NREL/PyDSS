from collections import defaultdict

import pandas as pd
import numpy as np
import os

import toml

from pydss.config_data import convert_config_data_to_toml
from pydss.registry import Registry
from pydss.utils.utils import load_data
from pydss.exceptions import InvalidConfiguration, InvalidParameter

class pyContrReader:
    def __init__(self, Path):
        self.pyControllers = {}
        filenames = os.listdir(Path)
        found_config_file = False
        found_excel_file = False
        for filename in filenames:
            pyControllerType, ext = os.path.splitext(filename)
            if filename.startswith('~$'):
                continue
            elif ext == '.xlsx':
                filename = convert_config_data_to_toml(filename)
            elif ext != ".toml":
                continue
            if pyControllerType not in self.pyControllers:
                self.pyControllers[pyControllerType] = {}
            filepath = os.path.join(Path, filename)
            assert (os.path.exists(filepath)), 'path: "{}" does not exist!'.format(filepath)
            for name, controller in load_data(filepath).items():
                if name in self.pyControllers[pyControllerType]:
                    raise InvalidParameter(
                        f"Multiple pydss controller definitions for a single OpenDSS element not allowed: {name}"
                    )
                self.pyControllers[pyControllerType][name] = controller


def read_controller_settings_from_registry(path):
    registry = Registry()
    controllers = defaultdict(dict)
    controller_settings = defaultdict(dict)
    filenames = os.listdir(path)
    for filename in filenames:
        controller_type, ext = os.path.splitext(filename)
        # This file contains a mapping of controller to an array of names.
        # The controller settings must be stored in the pydss registry.

        controller_to_name = load_data(os.path.join(path, filename))
        
        for controller, names in controller_to_name.items():
            settings = controller_settings[controller_type].get(controller)

            if settings is None:
                if not registry.is_controller_registered(controller_type, controller):
                    raise InvalidConfiguration(
                        f"{controller_type} / {controller} is not registered"
                    )
                settings = registry.read_controller_settings(controller_type, controller)
                controller_settings[controller_type][controller] = settings
            for name in names:
                controllers[controller_type][name] = settings

    return controllers


class pySubscriptionReader:
    def __init__(self, filePath):
        self.SubscriptionList = {}
        if not os.path.exists(filePath):
            raise FileNotFoundError('path: "{}" does not exist!'.format(filePath))

        for elem, elem_data in load_data(filePath).items():
            if elem_data["Subscribe"]:
                self.SubscriptionList[elem] = elem_data


class pyExportReader:
    def __init__(self, filePath):
        self.pyControllers = {}
        self.publicationList = []
        xlsx_filename = os.path.splitext(filePath)[0] + '.xlsx'
        if not os.path.exists(filePath) and os.path.exists(xlsx_filename):
            convert_config_data_to_toml(xlsx_filename)

        if not os.path.exists(filePath):
            raise FileNotFoundError('path: "{}" does not exist!'.format(filePath))

        for elem, elem_data in load_data(filePath).items():
            self.pyControllers[elem] = elem_data["Publish"][:]
            self.pyControllers[elem] += elem_data["NoPublish"]
            for item in elem_data["Publish"]:
                self.publicationList.append(f"{elem} {item}")

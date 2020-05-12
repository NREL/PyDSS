import pandas as pd
import numpy as np
import os

import toml

from PyDSS.config_data import convert_config_data_to_toml
from PyDSS.utils.utils import load_data
from PyDSS.exceptions import InvalidParameter

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
                        f"Multiple PyDSS controller definitions for a single OpenDSS element not allowed: {name}"
                    )
                self.pyControllers[pyControllerType][name] = controller


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

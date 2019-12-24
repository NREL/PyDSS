import pandas as pd
import numpy as np
import os

import toml

from PyDSS.config_data import convert_config_data_to_toml
from PyDSS.utils.utils import load_data


class pyContrReader:
    def __init__(self, Path):
        self.pyControllers = {}
        filenames = os.listdir(Path)
        found_config_file = False
        found_excel_file = False
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext == '.xlsx' and not filename.startswith('~$'):
                found_excel_file = True
                pyControllerType  = filename.split('.')[0]
                filepath = os.path.join(Path, filename)
                assert (os.path.exists(filepath)), 'path: "{}" does not exist!'.format(filepath)
                ControllerDataset = pd.read_excel(filepath, skiprows=[0,], index_col=[0])
                pyControllerNames = ControllerDataset.index.tolist()
                pyController = {}
                for pyControllerName in pyControllerNames:
                    pyControllerData = ControllerDataset.loc[pyControllerName]
                    assert len(pyControllerData == 1), 'Multiple PyDSS controller definitions for a single OpenDSS ' +\
                                                       'element not allowed'
                    pyControllerDict = pyControllerData.to_dict()
                    pyController[pyControllerName] = pyControllerDict
                self.pyControllers[pyControllerType] = pyController
            #elif ext == ".toml":
            #    with open(os.path.join(Path, filename)) as f_in:
            #        self.pyControllers = toml.load(f_in)
            #        found_config_file = True
            #    break

        assert not (found_config_file and found_excel_file), "Found both .xlsx files and a config file"

class pySubscriptionReader:
    def __init__(self, filePath):
        self.SubscriptionDict = {}
        assert (os.path.exists(filePath)), 'path: "{}" does not exist!'.format(filePath)
        SubscriptionData = pd.read_excel(filePath, skiprows=[0,], index_col=[0])
        requiredColumns = {'Property', 'Subscription ID', 'Unit', 'Subscribe', 'Data type'}
        fileColumns = set(SubscriptionData.columns)
        diff  = requiredColumns.difference(fileColumns)

        assert (len(diff) == 0), 'Missing column in the subscriptions file.\nRequired columns: {}'.format(
            requiredColumns
        )
        Subscribe = SubscriptionData['Subscribe']
        assert (Subscribe.dtype == bool), 'The subscribe column can only have boolean values.'
        self.SubscriptionDict = SubscriptionData.T.to_dict()


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

import pandas as pd
import numpy as np
import os

class pyContrReader:
    def __init__(self, Path):
        self.pyControllers = {}
        filenames = os.listdir(Path)
        for filename in filenames:
            if filename.endswith('.xlsx') and not filename.startswith('~$'):
                pyControllerType  = filename.split('.')[0]
                filepath = os.path.join(Path, filename)
                assert (os.path.exists(filepath)), 'path: "{}" does not exist!'.format(filepath)
                ControllerDataset = pd.read_excel(filepath, skiprows=[0,], index_col=[0])
                pyControllerNames = ControllerDataset.index.tolist()
                pyController = {}
                for pyControllerName in pyControllerNames:
                    pyControllerData = ControllerDataset.loc[pyControllerName]
                    assert len(pyControllerData == 1), 'Multiple pydss controller definitions for a single OpenDSS ' +\
                                                       'element not allowed'
                    pyControllerDict = pyControllerData.to_dict()
                    pyController[pyControllerName] = pyControllerDict
                self.pyControllers[pyControllerType] = pyController


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
        assert (os.path.exists(filePath)), 'path: "{}" does not exist!'.format(filePath)
        ControllerDataset = pd.read_excel(filePath, skiprows=[0,], index_col=[0])
        assert (ControllerDataset.columns[0] == 'Publish'), 'First column after class declarations in the ' +\
                                                            'export defination files  should have column ' +\
                                                            'name "Publish"'

        Publish = ControllerDataset['Publish']
        assert (Publish.dtype == bool), 'The publish column can only have boolean values.'
        ControllerDatasetFiltered = ControllerDataset[ControllerDataset.columns[1:]]

        pyControllerNames = ControllerDatasetFiltered.index.tolist()
        pyController = {}
        for pyControllerName, doPublish in zip(pyControllerNames, Publish.values):
            pyControllerData = ControllerDatasetFiltered.loc[pyControllerName]
            pulishdata = ControllerDataset['Publish'].loc[pyControllerName]
            if isinstance(pulishdata, np.bool_):
                pulishdata = [pulishdata]
            else:
                pulishdata = pulishdata.dropna().values
            Data = pyControllerData.copy()
            Data.index = range(len(Data))
            for i, publish in enumerate(pulishdata):
                if publish:
                    if isinstance(Data, pd.core.frame.DataFrame):
                        properties = Data.loc[i].dropna()
                    else:
                        properties = Data.dropna().values
                    for property in properties:
                        self.publicationList.append("{} {}".format(pyControllerName, property))

            if len(pyControllerData) > 1:
                pyControllerData = pd.Series(pyControllerData.values.flatten())
                pyControllerDict = pyControllerData.dropna().to_dict()
            else:
                pyControllerDict = pyControllerData.dropna().to_dict()

            self.pyControllers[pyControllerName] = pyControllerDict
        self.publicationList = list(set(self.publicationList))
import os
import pandas as pd


class pyContrReader:
    pyControllers = {}
    def __init__(self, Path = r'C:/Users/alatif/Desktop/PyDSS-heco/Import/pyControllerList'):
        self.pyControllers = {}
        filenames = os.listdir(Path)
        for filename in filenames:
            if filename.endswith('.xlsx'):
                pyControllerType  = filename.split('.')[0]
                ControllerDataset = pd.read_excel(os.path.join(Path, filename), skiprows=[0,], index_col=[0])
                pyControllerNames = ControllerDataset.index.tolist()
                pyController = {}
                for pyControllerName in pyControllerNames:
                    pyControllerData = ControllerDataset.loc[pyControllerName]
                    pyControllerDict = pyControllerData.to_dict()
                    pyController[pyControllerName] = pyControllerDict
                self.pyControllers[pyControllerType] = pyController

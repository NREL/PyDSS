import os
import pandas as pd

class pyPlotReader:
    pyPlots = {}

    def __init__(self, Path = r'C:/Users/alatif/Desktop/PyDSS-heco/Import/pyPlotList'):
        self.pyPlots = {}
        filenames = os.listdir(Path)
        for filename in filenames:
            if filename.endswith('.xlsx'):
                pyPlotType  = filename.split('.')[0]
                PlotDataset = pd.read_excel(os.path.join(Path, filename), skiprows= [0,], index_col = [0])
                pyPlotNames = PlotDataset.index.tolist()
                pyPlot = {}
                for pyPlotName in pyPlotNames:
                    pyPlotData = PlotDataset.loc[pyPlotName]
                    pyPlotDict = pyPlotData.to_dict()
                    pyPlot[pyPlotName] =  pyPlotDict
                self.pyPlots[pyPlotType] = pyPlot




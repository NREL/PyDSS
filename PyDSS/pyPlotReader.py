import os
import pandas as pd

from PyDSS.config_data import convert_config_data_to_toml
from PyDSS.utils.utils import load_data
from PyDSS.exceptions import InvalidParameter

class pyPlotReader:
    def __init__(self, Path):
        self.pyPlots = {}
        filenames = os.listdir(Path)
        found_config_file = False
        found_excel_file = False
        for filename in filenames:
            pyPlotType, ext = os.path.splitext(filename)
            if filename.startswith('~$'):
                continue
            elif ext == '.xlsx':
                filename = convert_config_data_to_toml(filename)
            elif ext != ".toml":
                continue
            if pyPlotType not in self.pyPlots:
                self.pyPlots[pyPlotType] = {}
            filepath = os.path.join(Path, filename)
            assert (os.path.exists(filepath)), 'path: "{}" does not exist!'.format(filepath)

            assert (os.path.exists(filepath)), 'path: "{}" does not exist!'.format(filepath)
            for name, plot in load_data(filepath).items():
                if name in self.pyPlots[pyPlotType]:
                    raise InvalidParameter(
                        f"Multiple PyDSS dynamic plot definitions of the same type with the same name not allowed: "
                        f"{name} already exists for plot type {pyPlotType}"
                    )
                self.pyPlots[pyPlotType][name] = plot

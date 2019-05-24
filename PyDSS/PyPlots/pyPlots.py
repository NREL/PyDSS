from PyDSS.PyPlots import Plots

from os.path import dirname, basename, isfile
import glob
modules = glob.glob(Plots.__path__[0]+"/*.py")
pythonFiles = [ basename(f)[:-3] for f in modules if isfile(f) and
                not f.endswith('__init__.py') and
                not f.endswith('pyPlots.py')]

PlotTypes = {}
for file in pythonFiles:
    exec('from PyDSS.PyPlots.Plots import {}'.format(file))
    exec('PlotTypes["{}"] = {}.{}'.format(file, file, file))

#print(PlotTypes)

def Create(PlotType, PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit):

        PlotObject = PlotTypes[PlotType](PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit)
        return PlotObject


defalultPO = {
        'Network layout': False,
        'Time series': False
    }

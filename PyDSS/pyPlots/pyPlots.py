from PyDSS.pyPlots import Plots

from os.path import dirname, basename, isfile
import glob
modules = glob.glob(Plots.__path__[0]+"/*.py")
pythonFiles = [ basename(f)[:-3] for f in modules if isfile(f) and
                not f.endswith('__init__.py') and
                not f.endswith('pyPlots.py')]

PlotTypes = {}
for file in pythonFiles:
    exec('from PyDSS.pyPlots.Plots import {}'.format(file))
    exec('PlotTypes["{}"] = {}.{}'.format(file, file, file))


def Create(PlotType, PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit, dssSolver):
    assert (PlotType in PlotTypes), "Defination for '{}' pyPlot not found. \n " \
                                                "Please define the controller in ~PyDSS\PyPlots\Plots".format(
        PlotType
    )
    PlotObject = PlotTypes[PlotType](PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit, dssSolver)
    return PlotObject


defalultPO = {
        'Network layout': False,
        'Time series': False
    }

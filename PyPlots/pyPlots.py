from os.path import dirname, basename, isfile
import glob
modules = glob.glob(dirname(__file__)+"/*.py")
pythonFiles = [ basename(f)[:-3] for f in modules if isfile(f) and
                not f.endswith('__init__.py') and
                not f.endswith('pyPlots.py')]

PlotTypes = {}
for file in pythonFiles:
    exec('from . import {}'.format(file))
    exec('PlotTypes["{}"] = {}.{}'.format(file, file, file))

def Create(PlotType, PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit):
    try:
        PlotObject = PlotTypes[PlotType](PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit)
        return PlotObject
    except:
        print ('The object dictionary does not contain ' + PlotType)
        return -1


defalultPO = {
        'Network layout': False,
        'Time series': False
    }

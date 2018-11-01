from os.path import dirname, basename, isfile
import glob
modules = glob.glob(dirname(__file__)+"/*.py")
pythonFiles = [ basename(f)[:-3] for f in modules if isfile(f) and
                not f.endswith('__init__.py') and
                not f.endswith('pyController.py')]

from PyDSS.dssElement import dssElement

ControllerTypes = {}

for file in pythonFiles:
    exec('from pyControllers import {}'.format(file))
    exec('ControllerTypes["{}"] = {}.{}'.format(file, file, file))


def Create(ElmName, ControllerType, Settings, ElmObjectList, dssInstance, dssSolver):
    try:
        print(ElmObjectList)
        relObject = ElmObjectList[ElmName]
    except:
        Index = dssInstance.Circuit.SetActiveElement(ElmName)
        if int(Index) >= 0:
            ElmObjectList[ElmName] = dssElement(dssInstance)
            relObject = ElmObjectList[ElmName]
        else:
            print('The controller dictionary does not contain ' + ControllerType)
            return -1
    ObjectController = ControllerTypes[ControllerType](relObject, Settings, dssInstance, ElmObjectList, dssSolver)
    return ObjectController

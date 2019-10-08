from os.path import dirname, basename, isfile
import glob

from  PyDSS.pyControllers import Controllers

modules = glob.glob(Controllers.__path__[0]+"/*.py")
pythonFiles = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py') ]

from PyDSS.dssElement import dssElement
ControllerTypes = {}

for file in pythonFiles:
    exec('from PyDSS.pyControllers.Controllers import {}'.format(file))
    exec('ControllerTypes["{}"] = {}.{}'.format(file, file, file))

def Create(ElmName, ControllerType, Settings, ElmObjectList, dssInstance, dssSolver):

    assert (ControllerType in ControllerTypes), "Defination for '{}' controller not found. \n " \
                                                "Please define the controller in ~PyDSS\pyControllers\Controllers".format(
        ControllerType
    )
    # try:
        #print(ElmObjectList)
    assert (ElmName in ElmObjectList), "'{}' does not exist in the PyDSS master object dictionary.".format(ElmName)
    relObject = ElmObjectList[ElmName]
    # except:
    #     Index = dssInstance.Circuit.SetActiveElement(ElmName)
    #     if int(Index) >= 0:
    #         ElmObjectList[ElmName] = dssElement(dssInstance)
    #         relObject = ElmObjectList[ElmName]
    # else:
    #     print('The controller dictionary does not contain {}'.format(ElmName))
    #     return -1


    ObjectController = ControllerTypes[ControllerType](relObject, Settings, dssInstance, ElmObjectList, dssSolver)
    return ObjectController

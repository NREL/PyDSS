import LoadController

ControllerTypes ={
    'LoadController': LoadController.LoadController
}


def Create(ElmName, ControllerType, ElmObjectList):
    try:
        relObject = ElmObjectList[ElmName]
    except:
        print 'The object dictionary does not contain ' + ElmName
        return -1
    try:
        ObjectController = ControllerTypes[ControllerType](relObject)
    except:
        print 'The controller dictionary does not contain ' + ControllerType
        return -1
    return ObjectController

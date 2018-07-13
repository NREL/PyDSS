from pyControllers import PvController, xfmrController, SocketController, StorageController, HybridController
from PyDSS.dssElement import dssElement

ControllerTypes = {
    'PV Controller'     : PvController.PvController,
    'Socket Controller' : SocketController.SocketController,
    'XFMR Controller'   : xfmrController.xfmrController,
    'Storage Controller': StorageController.StorageController,
    'Hybrid Controller' : HybridController.HybridController
}


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

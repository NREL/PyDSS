import PvController
import xfmrController
import SocketController
import StorageController
from dssElement import dssElement

ControllerTypes ={
    'PV Controller'     : PvController.PvController,
    'Socket Controller' : SocketController.SocketController,
    'XFMR Controller'   : xfmrController.xfmrController,
    'Storage Controller': StorageController.StorageController,
}


def Create(ElmName, ControllerType, Settings, ElmObjectList, dssInstance, dssSolver):
    try:
        relObject = ElmObjectList[ElmName]
    except:
        Index = dssInstance.Circuit.SetActiveElement(ElmName)
        if int(Index) >= 0:
            ElmObjectList[ElmName] = dssElement(dssInstance)
            relObject = ElmObjectList[ElmName]
        else:
            print ('The object dictionary does not contain ' + ElmName)
            return -1
    ObjectController = ControllerTypes[ControllerType](relObject, Settings, dssInstance, ElmObjectList, dssSolver)
    return ObjectController
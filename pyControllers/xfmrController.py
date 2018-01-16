import matplotlib.pyplot as plt
import math

class xfmrController:
    P_old = 0
    __Locked = False
    def __init__(self, RegulatorObj, Settings, dssInstance, ElmObjectList, dssSolver):

        self.__ControlledElm = RegulatorObj
        self.__ConnTransformerName = 'Transformer.' + self.__ControlledElm.GetParameter2('transformer').lower()
        self.__ConnTransformer = ElmObjectList[self.__ConnTransformerName]
        self.__ElmObjectList = ElmObjectList
        self.__RPFlocking = Settings['RPF locking']
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name

        print('Connected XFMR - ', self.__ControlledElm.GetParameter2('transformer'))
        return

    def Update(self, Time, UpdateResults):
        Powers = self.__ConnTransformer.GetVariable('Powers')
        Powers = Powers[:int(len(Powers)/2)][::2]
        P_new = sum((float(x)) for x in Powers)
        #print('Power - ', P_new)
        if self.__RPFlocking and self.P_old < 0:
            self.__Locked = self.__EnableLock()
            print('RPF dected')
        elif self.__RPFlocking and self.P_old > 0:
           self.__Locked = self.__DisableLock()
        else:
            pass
        self.P_old = P_new
        return 0

    def __EnableLock(self):
        self.__ControlledElm.SetParameter('enabled','False')
        return True

    def __DisableLock(self):
        self.__ControlledElm.SetParameter('enabled', 'True')
        return False


class LoadController:
    def __init__(self, ElmObject, Settings, dssInstance, ElmObjectList):
        self.__ControlledElm = ElmObject
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        print (self.__Name)
        return

    def Update(self):
        #print self.__ControlledElm.GetParameter('kW')
        return

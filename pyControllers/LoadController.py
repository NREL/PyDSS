class LoadController:
    def __init__(self,ElmObject):
        self.__ControlledElm = ElmObject
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'Cont_' +  Name
        return

    def Update(self):
        #print self.__ControlledElm.GetParameter('kW')
        return

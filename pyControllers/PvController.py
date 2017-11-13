class PvController:
    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.__ElmObjectList = ElmObjectList
        self.P_ControlDict = {
            'None'           : lambda: 0,
            'Peak Shaving'   : self.VWcontrol,}

        self.Q_ControlDict = {
            'None'           : lambda: 0,
            'CPF'            : self.CPFcontrol,
            'VPF'            : self.VPFcontrol,
            'VVar'           : self.VVARcontrol, }


        self.__ControlledElm = PvObj
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        print (self.__Name)
        return

    def Update(self, Time, UpdateResults):
        print ('Yolo')
        return 0

    def VWcontrol(self):
        return 0

    def VVARcontrol(self):
        return 0

    def CPFcontrol(self):
        return 0

    def VPFcontrol(self):
        return 0


class dssBus:
    __Name = None
    __Index = None
    __Variables = {}
    XY = None
    def __init__(self, dssInstance):
        self.__Name =  dssInstance.Bus.Name()

        self.__dssInstance = dssInstance
        self.Distance = dssInstance.Bus.Distance()
        BusVarDict = dssInstance.Bus.__dict__
        for key in BusVarDict.keys():
            try:
                self.__Variables[key] = getattr(dssInstance.Bus, key)
            except:
                self.__Variables[key] = None
                pass
        if self.GetVariable('X') is not None:
            self.XY = [self.GetVariable('X'),self.GetVariable('Y')]
        else:
            self.XY = [0, 0]
        return

    def GetInfo(self):
        return self.__Name

    def inVariableDict(self,VarName):
        if VarName in self.__Variables:
            return True
        else:
            return False

    def DataLength(self,VarName):
        self.__dssInstance.Circuit.SetActiveBus(self.__Name)
        VarValue = self.GetVariable(VarName)
        if  isinstance(VarValue, list):
            return len(VarValue) , 'List'
        elif isinstance(VarValue, str):
            return 1, 'String'
        elif isinstance(VarValue, int or float or bool):
            return 1, 'Number'
        else:
            return None,None

    def GetVariableNames(self):
        return self.__Variables.keys()

    def GetVariable(self,VarName):
        self.__dssInstance.Circuit.SetActiveBus(self.__Name)
        if VarName in self.__Variables:
            try:
                return self.__Variables[VarName]()
            except:
                print ('Unexpected error')
                return None
        else:
            print ('Invalid variable name')
            return None

    def SetVariable(self,VarName,Value):
        self.__dssInstance.Circuit.SetActiveBus(self.__Name)
        if VarName in self.__Variables:
            try:
                return self.__Variables[VarName](Value)
            except:
                print ('Error setting Value')
                return None
        else:
            print ('Invalid variable name')
            return None
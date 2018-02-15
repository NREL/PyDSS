from dssBus import dssBus

class dssCircuit:
    __Name = None
    __Variables = {}

    def __init__(self, dssInstance):

        self.__Name =  dssInstance.Circuit.Name()
        self.__dssInstance = dssInstance

        CktElmVarDict = dssInstance.Circuit.__dict__
        for key in CktElmVarDict.keys():
            try:
                self.__Variables[key] = getattr(dssInstance.Circuit, key)
            except:
                self.__Variables[key] = None
                pass
        return

    def GetInfo(self):
        return self.__Name

    def inVariableDict(self,VarName):
        if VarName in self.__Variables:
            return True
        else:
            return False

    def DataLength(self,VarName):
        if VarName in self.__Variables:
            VarValue = self.GetVariable(VarName)
        else:
            return 0, None
        if  isinstance(VarValue, list):
            return len(VarValue) , 'List'
        elif isinstance(VarValue, str):
            return 1, 'String'
        elif isinstance(VarValue, int or float or bool):
            return 1, 'Number'
        else:
            return 0, None

    def IsValidAttribute(self,VarName):
        if VarName in self.__Variables:
            return True
        else:
            return False

    def GetVariable(self,VarName):
        if VarName in self.__Variables:
            try:
                return self.__Variables[VarName]()
            except:
                print ('Unexpected error')
                return None
        else:
            print (VarName + ' is an invalid variable name for element ' + self.__Class + '.' + self.__Name)
            return None

    def SetVariable(self, Param, Value):
        self.__dssInstance.utils.run_command(self.__Class + '.' + self.__Name + '.' + Param + ' = ' + str(Value))
        return self.GetVariable(Param)


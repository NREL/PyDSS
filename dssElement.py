class dssElement:
    __Name = None
    __Class = None
    __Parameters = {}
    __Variables = {}
    Bus = None
    BusCount = None
    def __init__(self, dssInstance):
        self.__Class,  self.__Name =  dssInstance.Element.Name().split('.',1)
        self.__dssInstance = dssInstance

        PropertiesNames = self.__dssInstance.Element.AllPropertyNames()
        AS = range(len(PropertiesNames))
        for i, PptName in zip(AS, PropertiesNames):
            self.__Parameters[PptName] = str(i)

        if dssInstance.CktElement.Name() == dssInstance.Element.Name():
            CktElmVarDict = dssInstance.CktElement.__dict__
            for VarName in dssInstance.CktElement.AllVariableNames():
                CktElmVarDict[VarName] = None

            for key in CktElmVarDict.keys():
                try:
                    self.__Variables[key] = getattr(dssInstance.CktElement, key)
                except:
                    self.__Variables[key] = None
                    pass
            self.Bus = dssInstance.CktElement.BusNames()
            self.BusCount = len(self.Bus)


    def GetInfo(self):
        return self.__Class,  self.__Name

    def inVariableDict(self,VarName):
        if VarName in self.__Variables:
            return True
        else:
            return False

    def DataLength(self,VarName):
        VarValue = self.GetVariable(VarName)
        if  isinstance(VarValue, list):
            return len(VarValue) , 'List'
        elif isinstance(VarValue, str):
            return 1, 'String'
        elif isinstance(VarValue, int or float or bool):
            return 1, 'Number'
        else:
            return 0, None

    def GetVariable(self,VarName):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if self.__dssInstance.CktElement.Name() == self.__dssInstance.Element.Name():
            if VarName in self.__Variables:
                try:
                    return self.__Variables[VarName]()
                except:
                    print ('Unexpected error')
                    return None
            else:
                print ('Invalid variable name')
                return None
        else:
            print ('Object is not a circuit element')
            return None

    def SetParameter(self, Param, Value):
        self.__dssInstance.utils.run_command(self.__Class + '.' + self.__Name + '.' + Param + ' = ' + str(Value))
        self.GetParameter2(Param)


    def GetParameter2(self, Param):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if self.__dssInstance.Element.Name() == (self.__Class + '.' + self.__Name):
            NumberOfProperties = len(self.__dssInstance.Element.AllPropertyNames())
            for i in range(NumberOfProperties):
                PropertyName = self.__dssInstance.Properties.Name(str(i))
                if PropertyName.lower()== Param.lower():
                    X =self.__dssInstance.Properties.Value(str(i))
                    #print(self.__Class + '.' + self.__Name + '.' + Param + ' -> ' + str(X))
                    return X
            print('Invalid parameter for ' + self.__Class + ' class.')
            return None
        else:
            print('Could not set ' + self.__Class + '.' + self.__Name + ' as active element.')
            return None

    def GetParameter(self, Param):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if Param in self.__Parameters:
            try:
                return self.__dssInstance.Properties.Value(self.__Parameters[Param])
            except:
                print ('Unable to get the passed parameter (check function documentation).')
                return None
        else:
            print ('Invalid parameter for ' + self.__Class + ' class.')
            return None
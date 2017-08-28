class dssElement:
    __Name = None
    __Class = None
    __Parameters = {}
    __Variables = {}
    Bus = None
    BusCount = None
    def __init__(self, dssInstance):
        self.__Class,  self.__Name =  dssInstance.Element.Name().split('.')
        self.__dssInstance = dssInstance

        NumberOfProperties = self.__dssInstance.Element.NumProperties()

        for i in range(NumberOfProperties):
            self.__Parameters[self.__dssInstance.Properties.Name(str(i))] = str(i)

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

    def GetVariable(self,VarName):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if self.__dssInstance.CktElement.Name() == self.__dssInstance.Element.Name():
            if VarName in self.__Variables:
                try:
                    return self.__Variables[VarName]()
                except:
                    print 'Unexpected error'
                    return None
            else:
                print 'Invalid variable name'
                return None
        else:
            print 'Object is not a circuit element'
            return None


    def SetParameter(self, Param, Value):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if Param in self.__Parameters:
            try:
                #self.__dssInstance.Properties.Value(self.__Parameters[Param]) = '10'
                if self.__dssInstance.Properties.Value(self.__Parameters[Param]) == Value:
                    return 0
                else:
                    return -1
            except:
                print 'Unable to set the passed value (check data type or function documentation).'
                return -1
        else:
            print 'Invalid parameter for ' + self.__Class + ' class.'
            return -1

    def GetParameter(self, Param):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if Param in self.__Parameters:
            try:
                #print self.__Parameters[Param]
                return self.__dssInstance.Properties.Value(self.__Parameters[Param])
            except:
                print 'Unable to get the passed parameter (check function documentation).'
                return None
        else:
            print 'Invalid parameter for ' + self.__Class + ' class.'
            return None
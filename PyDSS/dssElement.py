from PyDSS.dssBus import dssBus
import ast
class dssElement:

    def __init__(self, dssInstance):
        self.__Name = None
        self.__Class = None
        self.__Parameters = {}
        self.__Variables = {}
        self.Bus = None
        self.BusCount = None
        self.sBus = []

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
            self.sBus = []
            for BusName in self.Bus:
                self.__dssInstance.Circuit.SetActiveBus(BusName)
                self.sBus.append(dssBus(self.__dssInstance))
            return


    def GetInfo(self):
        return self.__Class,  self.__Name

    def inVariableDict(self,VarName):
        if VarName in self.__Variables:
            return True
        else:
            return False

    def DataLength(self,VarName):
        if VarName in self.__Variables:
            VarValue = self.GetVariable(VarName)
        elif VarName in self.__Parameters:
            VarValue = self.GetParameter(VarName)
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

    def GetValue(self,VarName):
        if VarName in self.__Variables:
            VarValue = self.GetVariable(VarName)
        elif VarName in self.__Parameters:
            VarValue = self.GetParameter(VarName)
            if VarValue is not None:
                try:
                    VarValue = float(VarValue)
                except:
                    try:
                        VarValue = ast.literal_eval(VarValue)
                    except:
                        pass
                    pass
            else:
                VarValue = 0
        else:
            VarValue = 0
        return VarValue

    def IsValidAttribute(self,VarName):
        if VarName in self.__Variables:
            return True
        elif VarName in self.__Parameters:
            return True
        else:
            return False


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
                print (VarName + ' is an invalid variable name for element ' + self.__Class + '.' + self.__Name)
                return None
        else:
            print ('Object is not a circuit element')
            return None

    def SetParameter(self, Param, Value):
        self.__dssInstance.utils.run_command(self.__Class + '.' + self.__Name + '.' + Param + ' = ' + str(Value))
        return self.GetParameter(Param)


    def GetParameter(self, Param):
        self.__dssInstance.Circuit.SetActiveElement(self.__Class + '.' + self.__Name)
        if self.__dssInstance.Element.Name() == (self.__Class + '.' + self.__Name):
            x = self.__dssInstance.Properties.Value(Param)
            try:
                return float(x)
            except:
                return x
        else:
            print('Could not set ' + self.__Class + '.' + self.__Name + ' as active element.')
            return None

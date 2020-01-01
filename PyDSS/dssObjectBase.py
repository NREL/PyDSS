
import abc
 
from PyDSS.exceptions import InvalidParameter
from PyDSS.value_storage import ValueByLabel, ValueByNumber


class dssObjectBase(abc.ABC):

    VARIABLE_OUTPUTS_BY_LABEL = {}
    VARIABLE_OUTPUTS_COMPLEX = ()

    def __init__(self, dssInstance, name, fullName):
        self._Name = name
        self._FullName = fullName
        self._Variables = {}
        self._dssInstance = dssInstance

    @abc.abstractmethod
    def SetActiveObject(self):
        """Set the active DSS object."""

    def _get_labels(self, VarName):
        pass

    def DataLength(self, VarName):
        self.SetActiveObject()
        if VarName in self._Variables:
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

    def GetInfo(self):
        return self._Name

    def GetValue(self, VarName, convert=False):
        if VarName in self._Variables:
            VarValue = self.GetVariable(VarName, convert=convert)
        else:
            VarValue = -1
        return VarValue

    def GetVariable(self, VarName, convert=False):
        if VarName not in self._Variables:
            raise InvalidParameter(f'{VarName} is an invalid variable name for element {self._FullName}')

        self.SetActiveObject()
        func = self._Variables[VarName]
        if func is None:
            raise InvalidParameter(f"get function for {self._FullName} / {VarName} is None")

        value = func()
        if not convert:
            return value

        if VarName in self.VARIABLE_OUTPUTS_BY_LABEL:
            info = self.VARIABLE_OUTPUTS_BY_LABEL[VarName]
            label_prefix = info["label_prefix"]
            labels = getattr(self, info["accessor"])
            return ValueByLabel.create(self._FullName, VarName, label_prefix, labels, value)
        elif VarName in self.VARIABLE_OUTPUTS_COMPLEX:
            assert isinstance(value, list) and len(value) == 2, str(value)
            value = complex(value[0], value[1])
        return ValueByNumber(self._FullName, VarName, value)

    def GetVariableNames(self):
        return self._Variables.keys()

    def inVariableDict(self, VarName):
        return VarName in self._Variables

    def IsValidAttribute(self, VarName):
        return self.inVariableDict(VarName)

    @property
    def FullName(self):
        return self._Name

    @property
    def Name(self):
        return self._Name

    def SetVariable(self, VarName, Value):
        self.SetActiveObject()
        if VarName not in self._Variables:
            raise InvalidParameter(f"invalid variable name {VarName}")

        return self._Variables[VarName](Value)
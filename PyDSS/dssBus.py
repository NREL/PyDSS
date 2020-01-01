
from PyDSS.dssObjectBase import dssObjectBase


class dssBus(dssObjectBase):

    VARIABLE_OUTPUTS_BY_LABEL = {
        "PuVoltage": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
        "SeqVoltages": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
        "VMagAngle": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
        "Voc": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
        "Voltages": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
        "puVmagAngle": {
            "accessor": "Phases",
            "label_prefix": "Phase",
        },
    }
    VARIABLE_OUTPUTS_COMPLEX = ()

    def __init__(self, dssInstance):
        name = dssInstance.Bus.Name()
        super(dssBus, self).__init__(dssInstance, name, name)
        self._Index = None
        self.XY = None
        self._Nodes = dssInstance.Bus.Nodes()

        self.Distance = dssInstance.Bus.Distance()
        BusVarDict = dssInstance.Bus.__dict__
        for key in BusVarDict.keys():
            try:
                self._Variables[key] = getattr(dssInstance.Bus, key)
            except:
                self._Variables[key] = None
        if self.GetVariable('X') is not None:
            self.XY = [self.GetVariable('X'), self.GetVariable('Y')]
        else:
            self.XY = [0, 0]

    @property
    def NumPhases(self):
        return len(self._Nodes)

    @property
    def Phases(self):
        return self._Nodes[:]

    def SetActiveObject(self):
        self._dssInstance.Circuit.SetActiveBus(self._Name)

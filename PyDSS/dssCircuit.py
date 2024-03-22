import opendssdirect as dss

from pydss.dssObjectBase import dssObjectBase

class dssCircuit(dssObjectBase):

    VARIABLE_OUTPUTS_BY_LABEL = {}
    VARIABLE_OUTPUTS_BY_LIST = (
        "AllBusMagPu",
    )
    VARIABLE_OUTPUTS_COMPLEX = (
        "LineLosses",
        "Losses",
        "SubstationLosses",
        "TotalPower",
    )

    def __init__(self, dssInstance=None):
        if dssInstance is None:
            dssInstance = dss
        name = dssInstance.Circuit.Name()
        fullName = "Circuit." + name
        self._Class = 'Circuit'
        super(dssCircuit, self).__init__(dssInstance, name, fullName)

        CktElmVarDict = dssInstance.Circuit.__dict__
        for key in CktElmVarDict.keys():
            try:
                self._Variables[key] = getattr(dssInstance.Circuit, key)
            except:
                self._Variables[key] = None

    def SetActiveObject(self):
        pass

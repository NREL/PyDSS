from PyDSS.dssObjectBase import dssObjectBase
from PyDSS.dssElement import dssElement

class dssCircuit(dssObjectBase):

    VARIABLE_OUTPUTS_BY_LABEL = {
        "AllBusMagPu":{"is_complex": True, "units": ['[pu]']}}
    VARIABLE_OUTPUTS_COMPLEX = (
        "LineLosses",
        "Losses",
        "SubstationLosses",
        "TotalPower",
    )

    def __init__(self, dssInstance):
        name = dssInstance.Circuit.Name()
        fullName = "Circuit." + name
        self._Class = 'Circuit'
        super(dssCircuit, self).__init__(dssInstance, name, fullName)

        nodes = dssInstance.CktElement.NodeOrder()
        self._NumConductors = dssInstance.CktElement.NumConductors()
        n = self._NumConductors
        nodes = dssInstance.CktElement.NodeOrder()
        self._Nodes = [nodes[i * n:(i+1) * n] for i in range((len(nodes) + n -1) // n)]
        CktElmVarDict = dssInstance.Circuit.__dict__
        for key in CktElmVarDict.keys():
            try:
                self._Variables[key] = getattr(dssInstance.Circuit, key)
            except:
                self._Variables[key] = None

    def SetActiveObject(self):
        pass

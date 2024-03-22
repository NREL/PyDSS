
from pydss.dssElement import dssElement
from pydss.value_storage import ValueByNumber
from pydss.value_storage import ValueByList
import ast
from pydss.exceptions import InvalidParameter

class dssTransformer(dssElement):

    VARIABLE_OUTPUTS_BY_LABEL = {
        "Currents": {
            "is_complex": True,
            "units": ['[Amps]']
        },
        "CurrentsMagAng": {
            "is_complex": False,
            "units": ['[Amps]', '[Deg]']
        },
        "Powers": {
            "is_complex": True,
            "units": ['[kVA]']
        },
        "Voltages": {
            "is_complex": True,
            "units": ['[kV]']
        },
        'VoltagesMagAng': {
            "is_complex": False,
            "units": ['[kV]', '[Deg]']
        },
        'CplxSeqCurrents': {
            "is_complex": True,
            "units": ['[Amps]']
        },
        'SeqCurrents': {
            "is_complex": False,
            "units": ['[Amps]', '[Deg]']
        },
        'SeqPowers': {
            "is_complex": False,
            "units": ['[kVA]', '[Deg]']
        }
    }

    VARIABLE_OUTPUTS_COMPLEX = (
        'Losses',
    )

    VARIABLE_OUTPUTS_BY_LIST = [
        'taps'
    ]

    def __init__(self, dssInstance):
        super(dssTransformer, self).__init__(dssInstance)
        self._NumWindings = dssInstance.Transformers.NumWindings()
        self._dssInstance = dssInstance

    @property
    def NumWindings(self):
        return self._NumWindings

    @staticmethod
    def chunk_list(values, nLists):
        return [values[i * nLists:(i + 1) * nLists] for i in range((len(values) + nLists - 1) // nLists)]

    def GetValue(self, VarName, convert=False):
        if VarName in self._Variables:
            VarValue = self.GetVariable(VarName, convert=convert)
        elif VarName in self._Parameters:
            VarValue = self.GetParameter(VarName)
            if convert:
                if VarName in self.VARIABLE_OUTPUTS_BY_LIST:
                    VarValue = VarValue[:self.NumWindings]
                    VarValue = ValueByList(
                        self._FullName, VarName, VarValue, ['wdg{}'.format(i+1) for i in range(self.NumWindings)]
                    )
                else:
                    VarValue = ValueByNumber(self._FullName, VarName, VarValue)

        else:
            return None
        return VarValue

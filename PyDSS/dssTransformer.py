
from PyDSS.dssElement import dssElement

class dssTransformer(dssElement):
    def __init__(self, dssInstance):
        super(dssTransformer, self).__init__(dssInstance)
        self._NumWindings = dssInstance.Transformers.NumWindings()

    @property
    def NumWindings(self):
        return self._NumWindings

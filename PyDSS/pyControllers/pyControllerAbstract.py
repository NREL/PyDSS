import abc


class ControllerAbstract(abc.ABC):

    def __init__(self, controlledObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Abstract class CONSTRUCTOR."""

    def Update(self,  Priority, Time, UpdateResults):
        pass

    def Name(self):
        pass

    def ControlledElement(self):
        pass

    def debugInfo(self):
        pass
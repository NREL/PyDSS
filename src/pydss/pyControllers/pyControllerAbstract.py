import abc


class ControllerAbstract(abc.ABC):

    def __init__(self, controlledObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Abstract class CONSTRUCTOR."""
        pass

    @abc.abstractmethod
    def Update(self,  Priority, Time, UpdateResults):
        pass

    @abc.abstractmethod
    def Name(self):
        pass

    @abc.abstractmethod
    def ControlledElement(self):
        pass

    @abc.abstractmethod
    def debugInfo(self):
        pass
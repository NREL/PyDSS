from datetime import datetime, timedelta
import abc

class abstact_solver(abc.ABC):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        self.Settings = SimulationSettings
        self.pyLogger = Logger

        self._Time = datetime.strptime(SimulationSettings['Project']["Start time"], "%d/%m/%Y %H:%M:%S")

        self._StartTime = self._Time
        self._EndTime = self._Time
        self._dssIntance = dssInstance
        self._dssSolution = dssInstance.Solution
        stepres = SimulationSettings['Project']['Step resolution (sec)']
        mode = SimulationSettings['Project']['Simulation Type'].lower()
        self._sStepRes = stepres if mode != 'snapshot' else 1

    @abc.abstractmethod
    def setFrequency(self, frequency):
        return

    @abc.abstractmethod
    def getFrequency(self):
        return

    @abc.abstractmethod
    def SimulationSteps(self):
        return

    @abc.abstractmethod
    def IncStep(self):
        return

    @abc.abstractmethod
    def GetTotalSeconds(self):
        return

    @abc.abstractmethod
    def GetDateTime(self):
        return

    @abc.abstractmethod
    def GetStepResolutionSeconds(self):
        return

    @abc.abstractmethod
    def GetStepSizeSec(self):
        return

    @abc.abstractmethod
    def reSolve(self):
        return

    @abc.abstractmethod
    def Solve(self):
        return

    @abc.abstractmethod
    def getMode(self):
        return

    @abc.abstractmethod
    def setMode(self, mode):
        return

    @abc.abstractmethod
    def GetOpenDSSTime(self):
        return

    @abc.abstractmethod
    def MaxIterations(self):
        return

    def reset(self):

        return

from datetime import datetime, timedelta
from PyDSS.modes.abstract_solver import abstact_solver
import math

class Snapshot(abstact_solver):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        self.Settings = SimulationSettings
        self.pyLogger = Logger
        self._Time = datetime.strptime(SimulationSettings['Project']["Start time"], "%d/%m/%Y %H:%M:%S")
        self._StartTime = self._Time
        self._EndTime = self._Time + timedelta(minutes=SimulationSettings['Project']["Simulation duration (min)"])

        self.StartDay = (self._StartTime - datetime(self._StartTime.year, 1, 1)).days + 1
        self.EndDay = (self._EndTime - datetime(self._EndTime.year, 1, 1)).days + 1

        self._sStepRes = 1
        self._dssInstance = dssInstance
        self._dssSolution = dssInstance.Solution
        self._dssSolution.Mode(0)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(SimulationSettings['Project']['Control mode']))
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])
        return

    def SimulationSteps(self):
        return 1, self._StartTime, self._EndTime

    def GetOpenDSSTime(self):
        return self._dssSolution.DblHour()

    def GetDateTime(self):
        return self._Time

    @property
    def MaxIterations(self):
        return self.Settings['Project']['Max Control Iterations']

    def GetTotalSeconds(self):
        return (self._Time - self._StartTime).total_seconds()

    def GetStepResolutionSeconds(self):
        return self._sStepRes

    def GetStepSizeSec(self):
        return self._sStepRes

    def reSolve(self):
        return self._dssSolution.SolveNoControl()

    def Solve(self):
        self._dssSolution.Solve()

    def IncStep(self):
        return self._dssSolution.Solve()

    def setFrequency(self, frequency):
        self._dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return  self._dssSolution.Frequency()

    def setMode(self, mode):
        return self._dssInstance.utils.run_command('Set Mode={}'.format(mode))

    def getMode(self):
        return self._dssSolution.ModeID()
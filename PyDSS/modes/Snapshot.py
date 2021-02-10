from datetime import datetime, timedelta
from PyDSS.modes.abstract_solver import abstact_solver
import math

class Snapshot(abstact_solver):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        self.Settings = SimulationSettings
        self.pyLogger = Logger
        StartTimeMin = SimulationSettings['Project']['Start Time (min)']
        self._Time = datetime.strptime(
            '{} {}'.format(SimulationSettings['Project']['Start Year'], SimulationSettings['Project']['Start Day'] +
                           SimulationSettings['Project']['Date offset']), '%Y %j'
        )

        self._Time = self._Time + timedelta(minutes=StartTimeMin)
        self._StartTime = self._Time
        self._EndTime = self._Time
        self._sStepRes = 1
        self._dssInstance = dssInstance
        self._dssSolution = dssInstance.Solution
        self._dssSolution.Mode(0)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(SimulationSettings['Project']['Control mode']))
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])
        return

    def SimulationSteps(self):
        return 1, self._StartTime, self._EndTime

    def GetDateTime(self):
        return self._Time

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

    def IncrementTimeStep(self):
        pass

    def setFrequency(self, frequency):
        self._dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return  self._dssSolution.Frequency()

    def setMode(self, mode):
        return self._dssInstance.utils.run_command('Set Mode={}'.format(mode))

    def getMode(self):
        return self._dssSolution.ModeID()

    @property
    def MaxIterations(self):
        return self.Settings['Project']['Max Control Iterations']

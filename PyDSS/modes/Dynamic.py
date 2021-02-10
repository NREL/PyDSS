from PyDSS.modes.solver_base import solver_base
from datetime import datetime, timedelta
from PyDSS.common import DATE_FORMAT
import math

class Dynamic(solver_base):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        self.setMode('Dynamic')
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(self._MaxItrs)
        return

    def reset(self):
        self.setMode('Dynamic')
        self._dssSolution.Hour(self._Hour)
        self._dssSolution.Seconds(self._Second)
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(self._MaxItrs)
        return

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime % 60
        self._dssSolution.Hour(Hour)
        self._dssSolution.Seconds(Min*60)
        self._dssSolution.Number(mTimeStep)
        self._dssSolution.Solve()
        return

    def IncStep(self):
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.Solve()
        self._Time = self._Time + timedelta(seconds=self._sStepRes)
        self._Hour = int(self._dssSolution.DblHour() // 1)
        self._Second = (self._dssSolution.DblHour() % 1) * 60 * 60
        self.pyLogger.debug('OpenDSS time [h] - ' + str(self._dssSolution.DblHour()))
        self.pyLogger.debug('PyDSS datetime - ' + str(self._Time))

    def reSolve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.SolveNoControl()

    def Solve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.Solve()




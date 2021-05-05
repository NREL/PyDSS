from PyDSS.modes.solver_base import solver_base
from datetime import timedelta

class QSTS(solver_base):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        self._dssSolution.Mode(2)
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])
        self._dssSolution.DblHour(self._Hour + self._Second / 3600.0)
        return

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime%60
        self._dssSolution.DblHour(Hour + Min / 60.0)
        self._dssSolution.Number(mTimeStep)
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

    def IncStep(self):
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.Solve()
        self._Time = self._Time + timedelta(seconds=self._sStepRes)
        self._Hour = int(self._dssSolution.DblHour() // 1)
        self._Second = (self._dssSolution.DblHour() % 1) * 60 * 60
        return self._dssSolution.Converged()

    def reSolve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.SolveNoControl()
        return self._dssSolution.Converged()

    def Solve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

    def setMode(self, mode):
        self._dssInstance.utils.run_command('Set Mode={}'.format(mode))
        if mode.lower() == 'yearly':
            self._dssSolution.Mode(2)
            self._dssSolution.DblHour(self._Hour + self._Second / 3600.0)
            self._dssSolution.Number(1)
            self._dssSolution.StepSize(self._sStepRes)
            self._dssSolution.MaxControlIterations(self.Settings['Project']['Max Control Iterations'])

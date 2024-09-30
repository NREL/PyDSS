from datetime import timedelta
import math

from loguru import logger 

from pydss.modes.solver_base import solver_base
from pydss.simulation_input_models import ProjectModel


class Dynamic(solver_base):
    def __init__(self, dssInstance, settings: ProjectModel):
        super().__init__(dssInstance, settings)
        self.setMode('Dynamic')
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(settings.control_mode.value))
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(settings.max_control_iterations)
        self._dssSolution.DblHour(self._Hour + self._Second / 3600.0)
        return

    def setFrequency(self, frequency):
        self._dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return self._dssSolution.Frequency()

    def SimulationSteps(self):
        Seconds = (self._EndTime - self._StartTime).total_seconds()
        Steps = math.ceil(Seconds / self._sStepRes)
        return Steps, self._StartTime, self._EndTime

    def GetOpenDSSTime(self):
        return self._dssSolution.DblHour()

    def reset(self):
        self.setMode('Dynamic')
        self._dssSolution.Hour(self._Hour)
        self._dssSolution.Seconds(self._Second)
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(self._settings.project.max_control_iterations)
        return

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime % 60
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
        logger.debug('OpenDSS time [h] - ' + str(self._dssSolution.DblHour()))
        logger.debug('Pydss datetime - ' + str(self._Time))
        return self._dssSolution.Converged()

    def reSolve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.SolveNoControl()
        return self._dssSolution.Converged()

    def Solve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

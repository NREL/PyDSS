from datetime import timedelta

from pydss.modes.solver_base import solver_base
from pydss.simulation_input_models import ProjectModel
from pydss.utils.dss_utils import get_load_shape_resolution_secs
from pydss.utils.timing_utils import timer_stats_collector, track_timing


class QSTS(solver_base):
    def __init__(self, dssInstance, settings: ProjectModel):
        super().__init__(dssInstance, settings)
        self._dssSolution.Mode(2)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(settings.control_mode.value))
        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(settings.max_control_iterations)

        start_time_hours = self._Hour + self._Second / 3600.0
        load_shape_resolutions_secs = get_load_shape_resolution_secs()
        if load_shape_resolutions_secs == self._sStepRes:
            # I don't know why this is needed in this case.
            # The first data point gets skipped without it.
            # FIXME
            start_time_hours += self._sStepRes / 3600.0
        self._dssSolution.DblHour(start_time_hours)
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
            self._dssSolution.MaxControlIterations(self._settings.project.max_control_iterations)

    def reset(self):
        pass

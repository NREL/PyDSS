from PyDSS.modes.solver_base import solver_base
from PyDSS.simulation_input_models import SimulationSettingsModel
from PyDSS.utils.timing_utils import timer_stats_collector, track_timing


class Snapshot(solver_base):
    def __init__(self, dssInstance, settings: SimulationSettingsModel, Logger):
        super().__init__(dssInstance, settings, Logger)
        self._dssSolution.Mode(0)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(settings.project.control_mode.value))
        self._dssSolution.MaxControlIterations(settings.project.max_control_iterations)
        return

    @track_timing(timer_stats_collector)
    def reSolve(self):
        self._dssSolution.SolveNoControl()
        return self._dssSolution.Converged()

    def SimulationSteps(self):
        return 1, self._StartTime, self._EndTime

    @track_timing(timer_stats_collector)
    def Solve(self):
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

    @track_timing(timer_stats_collector)
    def IncStep(self):
        return self._dssSolution.Solve()

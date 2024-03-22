from pydss.modes.solver_base import solver_base
from pydss.simulation_input_models import ProjectModel


class Snapshot(solver_base):
    def __init__(self, dssInstance, settings: ProjectModel):
        super().__init__(dssInstance, settings)
        self._dssSolution.Mode(0)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(settings.control_mode.value))
        self._dssSolution.MaxControlIterations(settings.max_control_iterations)
        return

    def reSolve(self):
        self._dssSolution.SolveNoControl()
        return self._dssSolution.Converged()

    def SimulationSteps(self):
        return 1, self._StartTime, self._EndTime

    def Solve(self):
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

    def IncStep(self):
        return self._dssSolution.Solve()

    def SolveFor(self):
        pass

    def reset(self):
        pass

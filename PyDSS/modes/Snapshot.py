from PyDSS.modes.solver_base import solver_base

class Snapshot(solver_base):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        self._dssSolution.Mode(0)
        self._dssInstance.utils.run_command('Set ControlMode={}'.format(SimulationSettings['Project']['Control mode']))
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])
        return

    def reSolve(self):
        self._dssSolution.SolveNoControl()
        return self._dssSolution.Converged()

    def Solve(self):
        self._dssSolution.Solve()
        return self._dssSolution.Converged()

    def IncStep(self):
        return self._dssSolution.Solve()

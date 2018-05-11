import logging

def GetSolver(SimulationSettings ,dssInstance):
    LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
    pyLogger = logging.getLogger(LoggerTag)
    SolverDict = {
        'Snapshot': __Shapshot(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger),
        'Daily': __Daily(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger),
    }
    try:
        Solver = SolverDict[SimulationSettings['Simulation Type']]
        pyLogger.info('Solver set to ' + SimulationSettings['Simulation Type'] + ' mode.')
        return Solver
    except:
        pyLogger.error('Incorrect simulation type passed to the function.')
        return -1

class __Daily:
    def __init__(self, dssInstance, SimulationSettings, Logger):
        Logger.info('Simulation time step = ' + str(int(SimulationSettings['Step resolution (min)']*60)) + ' seconds')
        self.pyLogger = Logger
        self.StartDay = SimulationSettings['Start Day']
        self.sStepRes = int(SimulationSettings['Step resolution (min)']*60)
        self.__dssIntance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(2)
        self.__dssSolution.Hour(self.StartDay * 24)
        self.__dssSolution.Number(1)
        self.__dssSolution.StepSize(self.sStepRes)
        self.__dssSolution.MaxControlIterations(200)
        return

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime%60
        self.__dssSolution.Hour(Hour)
        self.__dssSolution.Seconds(Min*60)
        self.__dssSolution.Number(mTimeStep)
        self.__dssSolution.Solve()
        return

    def IncStep(self):
        self.__dssSolution.StepSize(self.sStepRes)
        self.__dssSolution.Solve()
        self.pyLogger.info('Simululation time [h] - ' + str(self.__dssSolution.DblHour()))

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.StepSizeMin(0)
        self.__dssSolution.SolveNoControl()

    def ResetTime(self):
        self.__dssSolution.Mode(2)
        self.__dssSolution.Hour(self.StartDay * 24)
        self.__dssSolution.Number(1)
        self.__dssSolution.StepSize(self.sStepRes)
        self.__dssSolution.MaxControlIterations(200)
        return

class __Shapshot:
    def __init__(self, dssInstance, SimulationSettings, Logger):
        self.__dssInstance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(0)
        self.__dssSolution.MaxControlIterations(100)
        self.OriginalStep = self.__dssSolution.Number()
        return

    def IncStep(self,CurrentTimeStep):
        self.timestep = timestep
        self.__dssSolution.Number(self.number)
        self.__dssSolution.Hour(timestep)
        self.__dssSolution.Seconds(0)

    def reSolve(self):
        self.__dssSolution.StepSizeMin(0)
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()



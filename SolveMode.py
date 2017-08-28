

def GetSolver(SimulationType,dssInstance):
    SolverDict = {
        'Snapshot': __Shapshot(dssInstance,  20),
    }
    try:
        Solver = SolverDict[SimulationType]
        print 'Solver set to ' + SimulationType + ' mode.'
        return Solver
    except:
        print 'Incorrect simulation type passed to the function.'
        return -1


class __Shapshot:
    def __init__(self, dssInstance, MaxIter = 20):
        self.__dssIntance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.MaxControlIterations(MaxIter)
        self.OriginalStep = self.__dssSolution.Number()
        return

    def IncStep(self,CurrentTimeStep):
        self.__dssSolution.InitSnap()
        iteration = 0
        while not self.__dssSolution.ControlActionsDone():
            self.__dssSolution.SolveNoControl()
            self.customControlLoop()
            self.__dssSolution.CheckControls()
            iteration += 1
            if iteration > self.__dssSolution.MaxControlIterations():
                print('No convergence @ time step - ' + str(CurrentTimeStep))
                break
        self.__dssSolution.FinishTimeStep()  # cleanup and increment time

    def customControlLoop(self):
        return
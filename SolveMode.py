

def GetSolver(SimulationType,dssInstance):
    SolverDict = {
        'Snapshot': __Shapshot(dssInstance,  20),
        'Daily': __Daily(dssInstance, 0),
    }
    try:
        Solver = SolverDict[SimulationType]
        print ('Solver set to ' + SimulationType + ' mode.')
        return Solver
    except:
        print ('Incorrect simulation type passed to the function.')
        return -1

class __Daily:
    def __init__(self, dssInstance, hour = 0, mStepResolution = 5):
        self.mStepRes = mStepResolution
        self.__dssIntance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(1)
        self.__dssSolution.Hour(hour)
        self.__dssSolution.Number(1)
        #self.__dssSolution.StepSizeHr = 0
        #self.__dssSolution.StepSizeMin = 5
        self.__dssSolution.StepSize(60)
        self.__dssSolution.MaxControlIterations(200)
        return

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime%60
        #print('Solving from '+ str(mStartTime)+ 'm to '+ str(mStartTime+mTimeStep)+ 'm')
        self.__dssSolution.Hour(Hour)
        self.__dssSolution.Seconds(Min*60)
        self.__dssSolution.Number(mTimeStep)
        self.__dssSolution.Solve()
        return

    def IncStep(self, CurrentTimeStep):
        self.__dssSolution.StepSize(60)
        self.__dssSolution.Solve()

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.Solve()

    def customControlLoop(self):
        return

class __Shapshot:
    def __init__(self, dssInstance, MaxIter = 2000):
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
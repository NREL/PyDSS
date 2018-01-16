

def GetSolver(SimulationType,dssInstance, mStepResolution, StartDay):
    SolverDict = {
        'Snapshot': __Shapshot(dssInstance,  20),
        'Daily': __Daily(dssInstance, StartDay = StartDay, mStepResolution = mStepResolution),
    }
    try:
        Solver = SolverDict[SimulationType]
        print ('Solver set to ' + SimulationType + ' mode.')
        return Solver
    except:
        print ('Incorrect simulation type passed to the function.')
        return -1

class __Daily:
    def __init__(self, dssInstance, StartDay = 0, mStepResolution = 15):
        self.mStepRes = mStepResolution
        self.__dssIntance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(2)
        self.__dssSolution.Hour(StartDay * 24)
        self.__dssSolution.Number(1)
        #self.__dssSolution.StepSizeHr = 0
        #self.__dssSolution.StepSizeMin = 5
        self.__dssSolution.StepSize(self.mStepRes*60)
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

    def IncStep(self):
        self.__dssSolution.StepSize(self.mStepRes*60)
        self.__dssSolution.Solve()
        print('Simululation time [h] - ', self.__dssSolution.DblHour())

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()

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
from datetime import datetime, timedelta
import logging
import math

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

        self.Settings = SimulationSettings
        self.pyLogger = Logger
        StartDay = SimulationSettings['Start Day']
        StartTimeMin = SimulationSettings['Start Time (min)']
        EndTimeMin = SimulationSettings['End Time (min)']
        sStepResolution = SimulationSettings['Step resolution (sec)']

        self.__Time = datetime.strptime('{} {}'.format(SimulationSettings['Start Year'],
                                                       SimulationSettings['Start Day'] + SimulationSettings[
                                                           'Date offset']
                                                       ), '%Y %j')
        self.__Time = self.__Time + timedelta(minutes=StartTimeMin)
        self.__StartTime = self.__Time
        self.__EndTime = datetime.strptime('{} {}'.format(SimulationSettings['Start Year'],
                                                       SimulationSettings['End Day'] + SimulationSettings[
                                                           'Date offset']
                                                       ), '%Y %j')

        self.__EndTime = self.__EndTime + timedelta(minutes=EndTimeMin)

        self.__sStepRes = sStepResolution
        self.__dssIntance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(2)
        self.__dssSolution.Hour(StartDay * 24)
        self.__dssSolution.Seconds(StartTimeMin * 60)
        self.__dssSolution.Number(1)
        self.__dssSolution.StepSize(self.__sStepRes)
        self.__dssSolution.MaxControlIterations(200)
        return

    def SimulationSteps(self):
        Seconds = (self.__EndTime - self.__StartTime).total_seconds()
        Steps = math.ceil(Seconds / self.__sStepRes)
        return Steps, self.__StartTime, self.__EndTime

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime%60
        self.__dssSolution.Hour(Hour)
        self.__dssSolution.Seconds(Min*60)
        self.__dssSolution.Number(mTimeStep)
        self.__dssSolution.Solve()
        return

    def IncStep(self):
        self.__dssSolution.StepSize(self.__sStepRes)
        self.__dssSolution.Solve()
        self.__Time = self.__Time + timedelta(seconds=self.__sStepRes)
        self.pyLogger.info('OpenDSS time [h] - ' + str(self.__dssSolution.DblHour()))
        self.pyLogger.info('PyDSS datetime - ' + str(self.__Time))

    def GetDateTime(self):
        return self.__Time

    def GetStepResolutionSeconds(self):
        return self.__sStepRes

    def GetStepSizeSec(self):
        return self.__sStepRes

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()

class __Shapshot:
    def __init__(self, dssInstance, SimulationSettings, Logger):
        self.__dssInstance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(0)
        self.__dssSolution.MaxControlIterations(100)
        self.OriginalStep = self.__dssSolution.Number()
        return

    def IncStep(self, CurrentTimeStep):
        self.timestep = CurrentTimeStep
        self.__dssSolution.Number(self.number)
        self.__dssSolution.Hour(CurrentTimeStep)
        self.__dssSolution.Seconds(0)

    def reSolve(self):
        self.__dssSolution.StepSizeMin(0)
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()



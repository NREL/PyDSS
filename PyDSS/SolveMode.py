from datetime import datetime, timedelta
import logging
import math

def GetSolver(SimulationSettings ,dssInstance):
    LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
    pyLogger = logging.getLogger(LoggerTag)
    try:
        pyLogger.info('Setting solver to ' + SimulationSettings['Simulation Type'] + ' mode.')
        if SimulationSettings['Simulation Type'].lower() == 'snapshot':
            return __Shapshot(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
        elif SimulationSettings['Simulation Type'].lower() == 'qsts':
            return __QSTS(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
        elif SimulationSettings['Simulation Type'].lower() == 'dynamic':
            return __Dynamic(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
        else:
            pyLogger.error('Invalid solver mode chosen')
            return -1
    except:
        pyLogger.error('Incorrect simulation type passed to the function.')
        return -1

class __Dynamic:
    def __init__(self, dssInstance, SimulationSettings, Logger):
        print('Running Dynamic simulation')
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
        #self.__dssSolution.Mode(10)
        self.setMode('Dynamic')
        self.__dssSolution.Hour(StartDay * 24)
        self.__dssSolution.Seconds(StartTimeMin * 60)
        self.__dssSolution.Number(1)
        self.__dssSolution.StepSize(self.__sStepRes)
        self.__dssSolution.MaxControlIterations(SimulationSettings['Max Control Iterations'])
        return

    def setFrequency(self, frequency):
        self.__dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return  self.__dssSolution.Frequency()

    def SimulationSteps(self):
        Seconds = (self.__EndTime - self.__StartTime).total_seconds()
        Steps = math.ceil(Seconds / self.__sStepRes)
        return Steps, self.__StartTime, self.__EndTime

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime % 60
        self.__dssSolution.Hour(Hour)
        self.__dssSolution.Seconds(Min*60)
        self.__dssSolution.Number(mTimeStep)
        self.__dssSolution.Solve()
        return

    def IncStep(self):
        self.__dssSolution.StepSize(self.__sStepRes)
        self.__dssSolution.Solve()
        self.__Time = self.__Time + timedelta(seconds=self.__sStepRes)
        self.__Hour = int(self.__dssSolution.DblHour() // 1)
        self.__Second = (self.__dssSolution.DblHour() % 1) * 60 * 60
        self.pyLogger.debug('OpenDSS time [h] - ' + str(self.__dssSolution.DblHour()))
        self.pyLogger.debug('PyDSS datetime - ' + str(self.__Time))

    def GetTotalSeconds(self):
        return (self.__Time - self.__StartTime).total_seconds()

    def GetDateTime(self):
        return self.__Time

    def GetStepResolutionSeconds(self):
        return self.__sStepRes

    def GetStepSizeSec(self):
        return self.__sStepRes

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()

    def getMode(self):
        return self.__dssSolution.ModeID()

    def setMode(self, mode):
        self.__dssIntance.utils.run_command('Set Mode={}'.format(mode))

class __QSTS:
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
        self.__dssSolution.MaxControlIterations(SimulationSettings['Max Control Iterations'])
        return
    def setFrequency(self, frequency):
        self.__dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return  self.__dssSolution.Frequency()

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
        #self.__sStepRes = 1/240
        self.__dssSolution.StepSize(self.__sStepRes)
        self.__dssSolution.Solve()
        self.__Time = self.__Time + timedelta(seconds=self.__sStepRes)
        self.__Hour = int(self.__dssSolution.DblHour() // 1)
        self.__Second = (self.__dssSolution.DblHour() % 1) * 60 * 60
        self.pyLogger.debug('OpenDSS time [h] - ' + str(self.__dssSolution.DblHour()))
        self.pyLogger.debug('PyDSS datetime - ' + str(self.__Time))

    def GetTotalSeconds(self):
        return (self.__Time - self.__StartTime).total_seconds()

    def GetDateTime(self):
        return self.__Time

    def GetStepResolutionSeconds(self):
        return self.__sStepRes

    def GetStepSizeSec(self):
        return self.__sStepRes

    def reSolve(self):
        self.__dssSolution.StepSize(0)
        self.__dssSolution.SolveNoControl()

    def getMode(self):
        return self.__dssSolution.ModeID()

    def setMode(self, mode):
        self.__dssIntance.utils.run_command('Set Mode={}'.format(mode))
        if mode.lower() == 'yearly':
            self.__dssSolution.Mode(2)
            self.__dssSolution.Hour(self.__Hour)
            self.__dssSolution.Seconds(self.__Second)
            self.__dssSolution.Number(1)
            self.__dssSolution.StepSize(self.__sStepRes)
            self.__dssSolution.MaxControlIterations(self.Settings['Max Control Iterations'])

class __Shapshot:
    def __init__(self, dssInstance, SimulationSettings, Logger):
        self.Settings = SimulationSettings
        self.pyLogger = Logger
        StartTimeMin = SimulationSettings['Start Time (min)']
        self.__Time = datetime.strptime(
            '{} {}'.format(SimulationSettings['Start Year'], SimulationSettings['Start Day'] +
                           SimulationSettings['Date offset']), '%Y %j'
        )

        self.__Time = self.__Time + timedelta(minutes=StartTimeMin)
        self.__StartTime = self.__Time
        self.__EndTime = self.__Time
        self.__sStepRes = 1
        self.__dssInstance = dssInstance
        self.__dssSolution = dssInstance.Solution
        self.__dssSolution.Mode(0)
        self.__dssInstance.utils.run_command('Set ControlMode={}'.format(SimulationSettings['Control mode']))
        self.__dssSolution.MaxControlIterations(SimulationSettings['Max Control Iterations'])

        return

    def SimulationSteps(self):
        return 1, self.__StartTime, self.__EndTime

    def GetDateTime(self):
        return self.__Time

    def GetTotalSeconds(self):
        return (self.__Time - self.__StartTime).total_seconds()

    def GetStepResolutionSeconds(self):
        return self.__sStepRes

    def GetStepSizeSec(self):
        return self.__sStepRes

    def reSolve(self):
        return self.__dssSolution.SolveNoControl()

    def IncStep(self):
        return self.__dssSolution.Solve()

    def setFrequency(self, frequency):
        self.__dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return  self.__dssSolution.Frequency()

    def setMode(self, mode):
        return self.__dssInstance.utils.run_command('Set Mode={}'.format(mode))

    def getMode(self):
        return self.__dssSolution.ModeID()
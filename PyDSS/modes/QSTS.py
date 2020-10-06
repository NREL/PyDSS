from datetime import datetime, timedelta
from PyDSS.modes.abstract_solver import abstact_solver
import math

class QSTS(abstact_solver):
    def __init__(self, dssInstance, SimulationSettings, Logger):
        super().__init__(dssInstance, SimulationSettings, Logger)
        print("Entered QSTS mode")
        self.Settings = SimulationSettings
        self.pyLogger = Logger
        StartDay = SimulationSettings['Project']['Start Day']
        StartTimeMin = SimulationSettings['Project']['Start Time (min)']
        EndTimeMin = SimulationSettings['Project']['End Time (min)']
        sStepResolution = SimulationSettings['Project']['Step resolution (sec)']

        self._Time = datetime.strptime('{} {}'.format(SimulationSettings['Project']['Start Year'],
                                                       SimulationSettings['Project']['Start Day'] +
                                                       SimulationSettings['Project'][
                                                           'Date offset']
                                                       ), '%Y %j')
        self._Time = self._Time + timedelta(minutes=StartTimeMin)
        self._StartTime = self._Time
        self._EndTime = datetime.strptime('{} {}'.format(SimulationSettings['Project']['Start Year'],
                                                          SimulationSettings['Project']['End Day'] +
                                                          SimulationSettings['Project'][
                                                              'Date offset']
                                                          ), '%Y %j')

        self._EndTime = self._EndTime + timedelta(minutes=EndTimeMin)
        self._sStepRes = sStepResolution
        self._dssIntance = dssInstance
        self._dssSolution = dssInstance.Solution
        self._dssSolution.Mode(2)

        self._dssSolution.Hour((StartDay - 1) * 24)
        self._dssSolution.Seconds((StartTimeMin + 0.50000001) * 60.0)
        self.reSolve()

        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])

        return


    def setFrequency(self, frequency):
        self._dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return self._dssSolution.Frequency()

    def SimulationSteps(self):
        Seconds = (self._EndTime - self._StartTime).total_seconds()
        Steps = math.ceil(Seconds / self._sStepRes)
        return Steps, self._StartTime, self._EndTime

    def SolveFor(self, mStartTime, mTimeStep):
        Hour = int(mStartTime/60)
        Min = mStartTime%60
        self._dssSolution.Hour(Hour)
        self._dssSolution.Seconds(Min*60)
        self._dssSolution.Number(mTimeStep)
        self._dssSolution.Solve()
        return

    def IncStep(self):
        #self.__sStepRes = 1/240
        self._dssSolution.StepSize(self._sStepRes)
        self._dssSolution.Solve()
        self._Time = self._Time + timedelta(seconds=self._sStepRes)
        self._Hour = int(self._dssSolution.DblHour() // 1)
        self._Second = (self._dssSolution.DblHour() % 1) * 60 * 60
        #self.pyLogger.info('OpenDSS time [h] - ' + str(self._dssSolution.DblHour()))
        #self.pyLogger.info('PyDSS datetime - ' + str(self._Time))

    def GetOpenDSSTime(self):
        return self._dssSolution.DblHour() #- self._sStepRes/3600

    def GetTotalSeconds(self):
        return (self._Time - self._StartTime).total_seconds()

    def GetDateTime(self):
        return self._Time

    def GetStepResolutionSeconds(self):
        return self._sStepRes

    def GetStepSizeSec(self):
        return self._sStepRes

    def reSolve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.SolveNoControl()

    def Solve(self):
        self._dssSolution.StepSize(0)
        self._dssSolution.Solve()

    def getMode(self):
        return self._dssSolution.ModeID()

    def setMode(self, mode):
        self._dssIntance.utils.run_command('Set Mode={}'.format(mode))
        if mode.lower() == 'yearly':
            self._dssSolution.Mode(2)
            self._dssSolution.Hour(self._Hour)
            self._dssSolution.Seconds(self._Second)
            self._dssSolution.Number(1)
            self._dssSolution.StepSize(self._sStepRes)
            self._dssSolution.MaxControlIterations(self.Settings['Project']['Max Control Iterations'])

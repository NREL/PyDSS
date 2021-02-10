from datetime import datetime, timedelta
from PyDSS.common import DATE_FORMAT
import math
#import abc

class solver_base:
    def __init__(self, dssInstance, SimulationSettings, Logger):

        self.Settings = SimulationSettings
        self.pyLogger = Logger

        self._Time = datetime.strptime(SimulationSettings['Project']["Start time"], DATE_FORMAT)
        self._Loadshape_init_time = datetime.strptime(SimulationSettings['Project']["Loadshape start time"],
                                                      DATE_FORMAT)
        time_offset_days = (self._Time - self._Loadshape_init_time).days
        time_offset_seconds = (self._Time - self._Loadshape_init_time).seconds
        # print(time_offset_days, time_offset_seconds)
        # quit()
        self._StartTime = self._Time
        self._EndTime = self._Time + timedelta(minutes=SimulationSettings['Project']["Simulation duration (min)"])
        StartDay = (self._StartTime - datetime(self._StartTime.year, 1, 1)).days + 1 + time_offset_days
        StartTimeMin = self._StartTime.minute + time_offset_seconds / 60.0
        sStepResolution = SimulationSettings['Project']['Step resolution (sec)']

        self.StartDay = (self._StartTime - datetime(self._StartTime.year, 1, 1)).days + 1
        self.EndDay = (self._EndTime - datetime(self._EndTime.year, 1, 1)).days + 1

        self._sStepRes = sStepResolution
        self._dssInstance = dssInstance
        self._dssSolution = dssInstance.Solution

        self._dssSolution.Hour((StartDay - 1) * 24)
        self._dssSolution.Seconds(StartTimeMin * 60.0)
        self.reSolve()

        self._dssSolution.Number(1)
        self._dssSolution.StepSize(self._sStepRes)
        self._MaxItrs = SimulationSettings['Project']['Max Control Iterations']
        self._dssSolution.MaxControlIterations(SimulationSettings['Project']['Max Control Iterations'])
        self.pyLogger.info("{} solver setup complete".format(SimulationSettings['Project']["Simulation Type"]))



    def setFrequency(self, frequency):
        self._dssSolution.Frequency(frequency)
        return

    def getFrequency(self):
        return self._dssSolution.Frequency()

    def SimulationSteps(self):
        Seconds = (self._EndTime - self._StartTime).total_seconds()
        Steps = math.ceil(Seconds / self._sStepRes)
        return Steps, self._StartTime, self._EndTime

    def GetTotalSeconds(self):
        return (self._Time - self._StartTime).total_seconds()

    def GetDateTime(self):
        return self._Time

    def GetStepResolutionSeconds(self):
        return self._sStepRes

    def GetStepSizeSec(self):
        return self._sStepRes

    def getMode(self):
        return self._dssSolution.ModeID()

    def setMode(self, mode):
        return

    def GetOpenDSSTime(self):
        return self._dssSolution.DblHour()

    @property
    def MaxIterations(self):
        return self.Settings['Project']['Max Control Iterations']

    def SolveFor(self, mStartTime, mTimeStep):
        raise Exception("Implement the 'SolveFor' function in the child class")
        return

    def reset(self):
        raise Exception("Implement the 'reset' function in the child class")
        return

    def reSolve(self):
        raise Exception("Implement the 'reSolve' function in the child class")
        return

    def Solve(self):
        raise Exception("Implement the 'Solve' function in the child class")
        return

    def IncStep(self):
        raise Exception("Implement the 'IncStep' function in the child class")
        return
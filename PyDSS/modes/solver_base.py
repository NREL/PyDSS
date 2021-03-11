from datetime import datetime, timedelta
from PyDSS.common import DATE_FORMAT
import math

class solver_base:
    def __init__(self, dssInstance, SimulationSettings, Logger):

        self.Settings = SimulationSettings
        self.pyLogger = Logger

        self._Time = datetime.strptime(SimulationSettings['Project']["Start time"], DATE_FORMAT)
        self._Loadshape_init_time = datetime.strptime(SimulationSettings['Project']["Loadshape start time"],
                                                      DATE_FORMAT)
        time_offset_days = (self._Time - self._Loadshape_init_time).days
        time_offset_seconds = (self._Time - self._Loadshape_init_time).seconds

        self._StartTime = self._Time
        self._EndTime = self._Time + timedelta(minutes=SimulationSettings['Project']["Simulation duration (min)"])

        StartDay = time_offset_days
        StartTimeMin = time_offset_seconds / 60.0
        sStepResolution = SimulationSettings['Project']['Step resolution (sec)']

        self.StartDay = self._StartTime.timetuple().tm_yday
        self.EndDay = self._EndTime.timetuple().tm_yday

        self._sStepRes = sStepResolution
        self._dssInstance = dssInstance
        self._dssSolution = dssInstance.Solution

        self._Hour = StartDay * 24
        self._Second = StartTimeMin * 60.0

        #self._dssSolution.DblHour()
        self.reSolve()
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
        return self._dssInstance.utils.run_command('Set Mode={}'.format(mode))

    def GetOpenDSSTime(self):
        return self._dssSolution.DblHour()

    @property
    def MaxIterations(self):
        return self.Settings['Project']['Max Control Iterations']

    def SolveFor(self, mStartTime, mTimeStep):
        raise Exception("Implement the 'SolveFor' function in the child class")

    def reset(self):
        raise Exception("Implement the 'reset' function in the child class")

    def reSolve(self):
        raise Exception("Implement the 'reSolve' function in the child class")

    def Solve(self):
        raise Exception("Implement the 'Solve' function in the child class")

    def IncStep(self):
        raise Exception("Implement the 'IncStep' function in the child class")
from datetime import datetime, timedelta
import math

from PyDSS.common import DATE_FORMAT
from PyDSS.simulation_input_models import SimulationSettingsModel

class solver_base:
    def __init__(self, dssInstance, settings: SimulationSettingsModel, Logger):

        self._settings = settings
        self.pyLogger = Logger

        self._Time = settings.project.start_time
        self._Loadshape_init_time = settings.project.loadshape_start_time
        time_offset_days = (self._Time - self._Loadshape_init_time).days
        time_offset_seconds = (self._Time - self._Loadshape_init_time).seconds

        self._StartTime = self._Time
        self._EndTime = self._Time + timedelta(minutes=settings.project.simulation_duration_min)

        StartDay = time_offset_days
        StartTimeMin = time_offset_seconds / 60.0
        sStepResolution = settings.project.step_resolution_sec

        self.StartDay = self._StartTime.timetuple().tm_yday
        self.EndDay = self._EndTime.timetuple().tm_yday

        self._sStepRes = sStepResolution
        self._dssInstance = dssInstance
        self._dssSolution = dssInstance.Solution

        self._Hour = StartDay * 24
        self._Second = StartTimeMin * 60.0

        #self._dssSolution.DblHour()
        self.reSolve()
        self.pyLogger.info("%s solver setup complete", settings.project.simulation_type)

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
        return self._settings.project.max_control_iterations

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

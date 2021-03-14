from datetime import datetime, timedelta
import logging
import math
import abc
from PyDSS.pyLogger import getLoggerTag
from PyDSS.modes.Dynamic import Dynamic
from PyDSS.modes.Snapshot import Snapshot
from PyDSS.modes.QSTS import QSTS



def GetSolver(SimulationSettings, dssInstance):
    if SimulationSettings["Logging"]["Pre-configured logging"]:
        LoggerTag = __name__
    else:
        LoggerTag = getLoggerTag(SimulationSettings)
    pyLogger = logging.getLogger(LoggerTag)

    pyLogger.info('Setting solver to ' + SimulationSettings['Project']['Simulation Type'] + ' mode.')
    if SimulationSettings['Project']['Simulation Type'].lower() == 'snapshot':
        return Snapshot(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
    elif SimulationSettings['Project']['Simulation Type'].lower() == 'qsts':
        return QSTS(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
    elif SimulationSettings['Project']['Simulation Type'].lower() == 'dynamic':
        return Dynamic(dssInstance=dssInstance, SimulationSettings=SimulationSettings, Logger=pyLogger)
    else:
        pyLogger.error('Invalid solver mode chosen')
        return -1



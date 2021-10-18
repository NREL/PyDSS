import logging

from PyDSS.common import SimulationType
from PyDSS.pyLogger import getLoggerTag
from PyDSS.modes.Dynamic import Dynamic
from PyDSS.modes.Snapshot import Snapshot
from PyDSS.modes.QSTS import QSTS
from PyDSS.simulation_input_models import SimulationSettingsModel


def GetSolver(settings: SimulationSettingsModel, dssInstance):
    LoggerTag = getLoggerTag(settings)
    pyLogger = logging.getLogger(LoggerTag)

    pyLogger.info('Setting solver to %s mode.', settings.project.simulation_type.value)
    if settings.project.simulation_type == SimulationType.SNAPSHOT:
        return Snapshot(dssInstance=dssInstance, settings=settings, Logger=pyLogger)
    elif settings.project.simulation_type == SimulationType.QSTS:
        return QSTS(dssInstance=dssInstance, settings=settings, Logger=pyLogger)
    elif settings.project.simulation_type == SimulationType.DYNAMIC:
        return Dynamic(dssInstance=dssInstance, settings=settings, Logger=pyLogger)
    else:
        pyLogger.error('Invalid solver mode chosen %s', settings.project.simulation_type)
        return -1

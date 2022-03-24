import logging

import opendssdirect as dss

from PyDSS.common import SimulationType
from PyDSS.exceptions import InvalidParameter
from PyDSS.pyLogger import getLoggerTag
from PyDSS.modes.Dynamic import Dynamic
from PyDSS.modes.Snapshot import Snapshot
from PyDSS.modes.QSTS import QSTS
from PyDSS.simulation_input_models import ProjectModel, SimulationSettingsModel


def GetSolver(settings: SimulationSettingsModel, dssInstance):
    LoggerTag = getLoggerTag(settings)
    pyLogger = logging.getLogger(LoggerTag)

    pyLogger.info('Setting solver to %s mode.', settings.project.simulation_type.value)
    return get_solver_from_simulation_type(settings.project)


def get_solver_from_simulation_type(settings: ProjectModel):
    """Return a solver from the simulation type."""
    if settings.simulation_type == SimulationType.SNAPSHOT:
        return Snapshot(dssInstance=dss, settings=settings)
    elif settings.simulation_type == SimulationType.QSTS:
        return QSTS(dssInstance=dss, settings=settings)
    elif settings.simulation_type == SimulationType.DYNAMIC:
        return Dynamic(dssInstance=dss, settings=settings)
    raise InvalidParameter(f"{settings.simulation_type} does not have a supported solver")

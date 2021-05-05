
import enum
import os

import PyDSS
from PyDSS.utils.utils import load_data

DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f' # '%Y-%m-%d %H:%M:%S.%f', "%m/%d/%Y %H:%M:%S"

PLOTS_FILENAME = "plots.toml"
SIMULATION_SETTINGS_FILENAME = "simulation.toml"
MONTE_CARLO_SETTINGS_FILENAME = "MonteCarloSettings.toml"
OPENDSS_MASTER_FILENAME = "Master.dss"
SUBSCRIPTIONS_FILENAME = "Subscriptions.toml"
PROJECT_TAR = "project.tar"
PROJECT_ZIP = "project.zip"
PROFILE_MAPPING = "mapping.toml"
PROFILE_SRC_H5 = "profiles.h5"

class VisualizationType(enum.Enum):
    FREQUENCY_PLOT = "FrequencySweep"
    HISTOGRAM_PLOT = "Histogram"
    VOLTDIST_PLOT = "VoltageDistance"
    TIMESERIES_PLOT = "TimeSeries"
    TOPOLOGY_PLOT = "Topology"
    XY_PLOT = "XY"
    THREEDIM_PLOT = "ThreeDim"
    TABLE_PLOT = "Table"
    NETWORK_GRAPH = "NetworkGraph"

class ControllerType(enum.Enum):
    PV_CONTROLLER = "PvController"
    SOCKET_CONTROLLER = "SocketController"
    STORAGE_CONTROLLER = "StorageController"
    XMFR_CONTROLLER = "xmfrController"
    MOTOR_STALL = "MotorStall"
    PV_VOLTAGE_RIDETHROUGH = "PvVoltageRideThru"
    FAULT_CONTROLLER = "FaultController"
    THERMOSTATIC_LOAD_CONTROLLER = "ThermostaticLoad"
    GENERATOR_CONTROLLER = "GenController"


CONTROLLER_TYPES = tuple(x.value for x in ControllerType)
CONFIG_EXT = ".toml"


class ExportMode(enum.Enum):
    BY_CLASS = "ExportMode-byClass"
    BY_ELEMENT = "ExportMode-byElement"
    SUBSCRIPTIONS = 'Subscriptions'
    EXPORTS = "Exports"


def filename_from_enum(obj):
    return obj.value + CONFIG_EXT


TIMESERIES_PLOT_FILENAME = filename_from_enum(VisualizationType.TIMESERIES_PLOT)
PV_CONTROLLER_FILENAME = filename_from_enum(ControllerType.PV_CONTROLLER)
STORAGE_CONTROLLER_FILENAME = filename_from_enum(ControllerType.STORAGE_CONTROLLER)
SOCKET_CONTROLLER_FILENAME = filename_from_enum(ControllerType.XMFR_CONTROLLER)
XMFR_CONTROLLER_FILENAME = filename_from_enum(ControllerType.SOCKET_CONTROLLER)
EXPORT_BY_CLASS_FILENAME = filename_from_enum(ExportMode.BY_CLASS)
EXPORT_BY_ELEMENT_FILENAME = filename_from_enum(ExportMode.BY_ELEMENT)
EXPORTS_FILENAME = filename_from_enum(ExportMode.EXPORTS)


DEFAULT_SUBSCRIPTIONS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "ExportLists",
    SUBSCRIPTIONS_FILENAME,
)
DEFAULT_SIMULATION_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    SIMULATION_SETTINGS_FILENAME,
)
DEFAULT_CONTROLLER_CONFIG_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "pyControllerList",
    PV_CONTROLLER_FILENAME,
)
DEFAULT_VISUALIIZATION_CONFIG_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "pyPlotList",
    TIMESERIES_PLOT_FILENAME,
)
DEFAULT_PLOT_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    PLOTS_FILENAME
)
DEFAULT_EXPORT_BY_CLASS_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "ExportLists",
    EXPORT_BY_CLASS_FILENAME,
)
DEFAULT_EXPORT_BY_ELEMENT_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "ExportLists",
    EXPORTS_FILENAME,
)
DEFAULT_EXPORTS_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "ExportLists",
    EXPORT_BY_ELEMENT_FILENAME,
)
DEFAULT_MONTE_CARLO_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]),
    "PyDSS",
    "defaults",
    "Monte_Carlo",
    MONTE_CARLO_SETTINGS_FILENAME,
)

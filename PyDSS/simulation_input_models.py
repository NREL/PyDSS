"""Defines user input models for a simulation."""

import enum
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator, validator
from pydantic.json import isoformat, timedelta_isoformat

from PyDSS.common import (
    ControlMode,
    FileFormat,
    LoggingLevel,
    ReportGranularity,
    SimulationType,
    SnapshotTimePointSelectionMode,
    SIMULATION_SETTINGS_FILENAME,
)
from PyDSS.dataset_buffer import DEFAULT_MAX_CHUNK_BYTES
from PyDSS.utils.utils import dump_data, load_data


class InputsBaseModel(BaseModel):
    """Base class for all input models"""

    class Config:
        title = "InputsBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False
        allow_population_by_field_name = True

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        for key, val in data.items():
            if isinstance(val, enum.Enum):
                data[key] = val.value
            elif isinstance(val, datetime):
                data[key] = isoformat(val)
            elif isinstance(val, timedelta):
                data[key] = timedelta_isoformat(val)
            elif isinstance(val, Path):
                data[key] = str(val)

        return data


class SnapshotTimePointSelectionConfigModel(InputsBaseModel):
    """Defines the user inputs for auto-selecting snapshot time points."""

    mode: Optional[SnapshotTimePointSelectionMode] = Field(
        title="mode",
        description="Mode",
        default=SnapshotTimePointSelectionMode.NONE,
    )
    start_time: Optional[datetime] = Field(
        title="start_time",
        description="Start time in the load shape profiles",
        default="2020-1-1 00:00:00.0",
    )
    search_duration_min: Optional[float] = Field(
        title="search_duration_min",
        description="Duration in minutes to search in the load shape profiles",
        default=1440.0,
    )


class ScenarioPostProcessModel(InputsBaseModel):
    """Defines user inputs for a scenario post-process script."""

    script: str = Field(
        title="script",
        description="Post-process script",
    )
    config_file: str = Field(
        title="config_file",
        description="Post-process config file",
    )


class ScenarioModel(InputsBaseModel):
    """Defines the user inputs for a scenario."""

    name: str = Field(
        title="name",
        description="Name of scenario",
    )
    post_process_infos: Optional[List[ScenarioPostProcessModel]] = Field(
        title="post_process_infos",
        description="Post-process script descriptors",
        default=[],
    )
    snapshot_time_point_selection_config: SnapshotTimePointSelectionConfigModel = Field(
        title="snapshot_time_point_selection_config",
        description="Descriptor for auto-selecting snapshot time points",
        default=SnapshotTimePointSelectionConfigModel(),
    )


class SimulationRangeModel(InputsBaseModel):
    """Governs time range when control algorithms can run in a simulation. Does not affect
    simulation times.

    """

    start: str = Field(
        title="start",
        description="Time to start running control algorithms each day.",
        default="00:00:00",
    )
    end: str = Field(
        title="end",
        description="Time to stop running control algorithms each day.",
        default="23:59:59",
    )


class ProjectModel(InputsBaseModel):
    """Defines the user inputs for the project."""

    project_path: Optional[Path] = Field(
        title="project_path",
        description="Base path of project. Join with 'active_project' to get full path",
        alias="Project Path",
    )
    active_project: Optional[str] = Field(
        title="active_project",
        description="Active project name. Join with 'project_path' to get full path",
        alias="Active Project",
    )
    active_project_path: Optional[Path] = Field(
        title="active_project_path",
        description="Path to project. Auto-generated.",
        internal=True,
    )
    scenarios: List[ScenarioModel] = Field(
        title="scenarios",
        description="List of scenarios",
        alias="Scenarios",
        default=[],
    )
    active_scenario: Optional[str] = Field(
        title="active_scenario",
        description="Name of active scenario",
        alias="Active Scenario",
        default="",
    )
    start_time: Optional[datetime] = Field(
        title="start_time",
        description="Start time of simulation",
        default="2020-01-01 00:00:00.0",
        alias="Start time",
    )
    simulation_duration_min: Optional[float] = Field(
        title="simulation_duration_min",
        description="Simulation duration in minutes.",
        default=1440.0,
    )
    step_resolution_sec: Optional[float] = Field(
        title="step_resolution_sec",
        description="Time step resolution in seconds",
        alias="Step resolution (sec)",
        default=900.0,
    )
    loadshape_start_time: Optional[datetime] = Field(
        title="loadshape_start_time",
        description="Start time of loadshape profiles",
        alias="Loadshape start time",
        default="2020-01-01 00:00:00.0",
    )
    simulation_range: Optional[SimulationRangeModel] = Field(
        title="simulation_range",
        description="Restrict control algorithms and data collection to these hours. "
        "Useful for skipping night when simulating PV Systems.",
        alias="Simulation range",
        default=SimulationRangeModel(),
    )
    simulation_type: Optional[SimulationType] = Field(
        title="simulation_type",
        description="Type of simulation to run.",
        alias="Simulation Type",
        default=SimulationType.QSTS,
    )
    control_mode: Optional[ControlMode] = Field(
        title="control_mode",
        description="Simulation control mode",
        alias="Control mode",
        default=ControlMode.STATIC,
    )
    max_control_iterations: Optional[int] = Field(
        title="max_control_iterations",
        description="Maximum outer loop control iterations",
        alias="Max Control Iterations",
        default=50,
    )
    convergence_error_percent_threshold: Optional[float] = Field(
        title="convergence_error_percent_threshold",
        description="Convergence error threshold as a percent",
        alias="Convergence error percent threshold",
        default=0.0,
    )
    error_tolerance: Optional[float] = Field(
        title="error_tolerance",
        description="Error tolerance in per unit",
        alias="Error tolerance",
        default=0.001,
    )
    max_error_tolerance: Optional[float] = Field(
        title="max_error_tolerance",
        description="Abort simulation if a convergence error exceeds this value.",
        alias="Max error tolerance",
        default=0.0,
    )
    skip_export_on_convergence_error: Optional[bool] = Field(
        title="skip_export_on_convergence_error",
        description="Do not export data at a time point if there is a convergence error.",
        alias="Skip export on convergence error",
        default=True,
    )
    dss_file: Optional[str] = Field(
        title="dss_file",
        description="OpenDSS master filename",
        alias="DSS File",
        default="Master.dss",
    )
    dss_file_absolute_path: Optional[bool] = Field(
        title="dss_file_absolute_path",
        description="Set to true if 'dss_file' is an absolute path.",
        alias="DSS File Absolute Path",
        default=False,
    )
    disable_pydss_controllers: Optional[bool] = Field(
        title="disable_pydss_controllers",
        description="Allows disabling of the control algorithms",
        alias="Disable PyDSS controllers",
        default=False,
    )
    use_controller_registry: Optional[bool] = Field(
        title="use_controller_registry",
        description="Use local controller registry.",
        alias="Use Controller Registry",
        default=False,
    )

    @root_validator(pre=True)
    def pre_process(cls, values):
        # Correct legacy files.
        values.pop("Return Results", None)
        for val in ("Simulation Type", "simulation_type"):
            if val in values:
                if not isinstance(values[val], SimulationType):
                    values[val] = values[val].lower()

        old_duration = values.pop("Simulation duration (min)", None)
        if old_duration is not None:
            if "simulation_duration_min" in values:
                raise ValueError(
                    "'simulation_duration_min' is mutually exclusive with 'Simulation duration (min)'"
                )
            values["simulation_duration_min"] = old_duration
        return values

    @validator("project_path")
    def check_project_path(cls, val):
        if val is None:
            # We are being used in library mode rather than project mode.
            return val

        path = Path(val)
        if not path.exists():
            raise ValueError(f"project_path={val} does not exist")
        return val

    @validator("active_project")
    def check_active_project(cls, val, values):
        if values.get("project_path") is None:
            return None
            
        active_project_path = values["project_path"] / val
        if not active_project_path.exists():
            raise ValueError(f"project_path={active_project_path} does not exist")
        return val

    @validator("active_project_path")
    def assign_active_project_path(cls, val, values):
        if values.get("project_path") is None and not val:
            return val
        return values["project_path"] / values["active_project"]

    @validator("scenarios")
    def check_scenarios(cls, val, values):
        if values.get("project_path") is None:
            return val

        if not val:
            raise ValueError("project['scenarios'] cannot be empty")
        return val

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        data.pop("active_project_path")
        return data


class ExportsModel(InputsBaseModel):
    """Defines the user inputs for defining data exports."""

    export_results: Optional[bool] = Field(
        title="export_results",
        description="Set to true to export circuit element values at each time point.",
        default=False,
        alias="Log Results",
    )
    export_elements: Optional[bool] = Field(
        title="export_elements",
        description="Set to true to export static information for all circuit elements.",
        default=True,
        alias="Export Elements",
    )
    export_element_types: Optional[list] = Field(
        title="export_element_types",
        description="Restrict 'export_elements' to these element types. Default is all types",
        default=[],
        alias="Export Element Types",
    )
    export_data_tables: Optional[bool] = Field(
        title="export_data_tables",
        description="Set to true to export circuit element data in tabular files. While it does "
                    "duplicate data, it provides a way to preserve a human-readable "
                    "dataset that does not require PyDSS to interpret.",
        default=True,
        alias="Export Data Tables",
    )
    export_pv_profiles: Optional[bool] = Field(
        title="export_pv_profiles",
        description="Set to true to export PV profiles to tabular files.",
        default=False,
        alias="Export PV Profiles",
    )
    export_data_in_memory: Optional[bool] = Field(
        title="export_data_in_memory",
        description="Set to true to keep circuit element data in memory rather than periodically "
        "flushing to an HDF5 file. This can be faster but will consume more memory.",
        default=False,
        alias="Export Data In Memory",
    )
    export_node_names_by_type: Optional[bool] = Field(
        title="export_node_names_by_type",
        description="Set to true to export node names by primary/secondary type to a file.",
        default=False,
        alias="Export Node Names By Type",
    )
    export_event_log: Optional[bool] = Field(
        title="export_event_log",
        description="Set to true to export the OpenDSS event log.",
        default=True,
        alias="Export Event Log",
    )
    export_format: Optional[FileFormat] = Field(
        title="export_format",
        description="Controls the file format used if export_data_tables is true.",
        default=FileFormat.HDF5,
        alias="Export Format",
    )
    export_compression: Optional[bool] = Field(
        title="export_compression",
        description="Set to true to compress data exported with 'export_data_tables'.",
        default=False,
        alias="Export Compression",
    )
    hdf_max_chunk_bytes: Optional[int] = Field(
        title="hdf_max_chunk_bytes",
        description="The chunk size in bytes to use for exported data in the HDF5 data store. "
                    "The value is passed to the h5py package. Refer to "
                    "http://docs.h5py.org/en/stable/high/dataset.html#chunked-storage for more "
                    "information.",
        default=DEFAULT_MAX_CHUNK_BYTES,
        alias="HDF Max Chunk Bytes",
    )

    @root_validator(pre=True)
    def pre_process(cls, values):
        values.pop("Return Results", None)
        values.pop("Export Mode", None)
        values.pop("Export Style", None)
        return values

    @validator("hdf_max_chunk_bytes")
    def check_hdf_max_chunk_bytes(cls, val):
        min = 16 * 1024
        if val < min:
            raise ValueError(f"hdf_max_chunk_bytes must be >= {min}")
        if val % 512 != 0:
            raise ValueError(f"hdf_max_chunk_bytes must be a multiple of 512")
        return val


class FrequencyModel(InputsBaseModel):
    """Defines the user inputs for defining frequency parameters."""

    enable_frequency_sweep: Optional[bool] = Field(
        title="enable_frequency_sweep",
        description="Enable harmonic sweep. Works with only 'Static' and 'QSTS' simulation modes.",
        default=False,
        alias="Enable frequency sweep",
    )
    fundamental_frequency: Optional[float] = Field(
        title="fundamental_frequency",
        description="Fundamental system frequeny in Hertz",
        default=60.0,
        alias="Fundamental frequency",
    )
    start_frequency: Optional[float] = Field(
        title="start_frequency",
        description="Start system frequeny in Hertz",
        default=1.0,
        alias="Start frequency",
    )
    end_frequency: Optional[float] = Field(
        title="end_frequency",
        description="End system frequeny in Hertz",
        default=15.0,
        alias="End frequency",
    )
    frequency_increment: Optional[float] = Field(
        title="frequency_increment",
        description="As multiple of fundamental",
        default=2.0,
        alias="frequency increment",
    )
    neglect_shunt_admittance: Optional[bool] = Field(
        title="neglect_shunt_admittance",
        description="Neglect shunt addmittance for frequency sweep",
        default=False,
        alias="Neglect shunt admittance",
    )
    percentage_load_in_series: Optional[float] = Field(
        title="percentage_load_in_series",
        description="Percent of load that is series RL for Harmonic studies",
        default=50.0,
        alias="Percentage load in series",
    )

    @validator("end_frequency")
    def check_end_frequency(cls, val, values):
        start = values["start_frequency"]
        if start > val:
            raise ValueError(f"start_frequency={start} must be less than end_frequency={val}")
        return val

    @validator("fundamental_frequency")
    def check_fundamental_frequency(cls, val):
        allowed = (50.0, 60.0)
        if val not in allowed:
            raise ValueError(f"fundamental_frequency must be one of {allowed}")
        return val

    @validator("percentage_load_in_series")
    def check_percentage_load_in_series(cls, val):
        if val < 0 or val > 100:
            raise ValueError(f"percentage_load_in_series must be between 0 and 100: {val}")
        return val


class HelicsModel(InputsBaseModel):
    """Defines the user inputs for HELICS."""

    co_simulation_mode: Optional[bool] = Field(
        title="co_simulation_mode",
        description="Set to true to enable the HELICS interface for co-simulation.",
        default=False,
        alias="Co-simulation Mode",
    )
    iterative_mode: Optional[bool] = Field(
        title="iterative_mode",
        description="Iterative mode",
        default=False,
        alias="Iterative Mode",
    )
    error_tolerance: Optional[float] = Field(
        title="error_tolerance",
        description="Error tolerance",
        default=0.0001,
        alias="Error tolerance",
    )
    max_co_iterations: Optional[int] = Field(
        title="max_co_iterations",
        description="Max number of co-simulation iterations",
        default=15,
        alias="Max co-iterations",
    )
    broker: Optional[str] = Field(
        title="broker",
        description="Broker name",
        default="mainbroker",
        alias="Broker",
    )
    broker_port: Optional[int] = Field(
        title="broker_port",
        description="Broker port",
        default=0,
        alias="Broker port",
    )
    federate_name: Optional[str] = Field(
        title="federate_name",
        description="Name of the federate",
        default="PyDSS",
        alias="Federate name",
    )
    time_delta: Optional[float] = Field(
        title="time_delta",
        description="The property controlling the minimum time delta for a federate.",
        default=0.01,
        alias="Time delta",
    )
    core_type: Optional[str] = Field(
        title="core_type",
        description="Core type to be use for communication",
        default="zmq",
        alias="Core type",
    )
    uninterruptible: Optional[bool] = Field(
        title="uninterruptible",
        description="Can the federate be interrupted",
        default=True,
        alias="Uninterruptible",
    )
    logging_level: Optional[int] = Field(
        title="logging_level",
        description="Logging level for the federate. Refer to HELICS documentation.",
        default=5,
        alias="Helics logging level",
    )

    @validator("logging_level")
    def check_logging_level(cls, val):
        if val < 0 or val > 10:
            raise ValueError(f"HELICS logging level must be between 0 and 10: {val}")
        return val

    @validator("max_co_iterations")
    def check_max_co_iterations(cls, val):
        if val < 1 or val > 1000:
            raise ValueError(f"max_co_iterations must be between 1 and 1000: {val}")
        return val


class LoggingModel(InputsBaseModel):
    """Defines the user inputs for controlling logging."""

    logging_level: Optional[LoggingLevel] = Field(
        title="logging_level",
        description="PyDSS minimum logging level",
        default=LoggingLevel.INFO,
        alias="Logging Level",
    )
    enable_console: Optional[bool] = Field(
        title="enable_console",
        description="Set to true to enable console logging.",
        default=True,
        alias="Display on screen",
    )
    enable_file: Optional[bool] = Field(
        title="enable_file",
        description="Set to true to enable logging to a file.",
        default=True,
        alias="Log to external file",
    )
    clear_old_log_file: Optional[bool] = Field(
        title="clear_old_log_file",
        description="Set to true to clear and overwrite any existing log files.",
        default=False,
        alias="Clear old log file",
    )
    log_time_step_updates: Optional[bool] = Field(
        title="log_time_step_updates",
        description="Set to true to log each completed time step.",
        default=True,
        alias="Log time step updates",
    )

    @root_validator(pre=True)
    def pre_process(cls, values):
        # Correct legacy files.
        for val in ("Logging Level", "logging_level"):
            if val in values:
                values[val] = values[val].lower()

        return values


class MonteCarloModel(InputsBaseModel):
    """Defines the user inputs for Monte Carlo simulations."""

    num_scenarios: Optional[int] = Field(
        title="num_scenarios",
        description="Number of Monte Carlo scenarios",
        default=-1,
        alias="Number of Monte Carlo scenarios",
    )


class PlotsModel(InputsBaseModel):
    """Defines the user inputs for plots."""

    create_dynamic_plots: Optional[bool] = Field(
        title="create_dynamic_plots",
        description="Enable rendering of dynamic plots using bokeh. Dependent on 'open_plots_in_browser'",
        default=False,
        alias="Create dynamic plots",
    )
    open_plots_in_browser: Optional[bool] = Field(
        title="open_plots_in_browser",
        description="Open plots in a browser.",
        default=True,
        alias="Open plots in browser",
    )


class ProfilesModel(InputsBaseModel):
    """Defines user inputs for the Profile Manager."""

    use_profile_manager: Optional[bool] = Field(
        title="use_profile_manager",
        description="Set to true to enable the Profile Manager.",
        default=False,
        alias="Use profile manager",
    )
    source_type: Optional[FileFormat] = Field(
        title="source_type",
        description="File format for source data",
        default=FileFormat.HDF5,
    )
    source: Optional[str] = Field(
        title="source",
        description="File containing source data",
        default="Profiles_backup.hdf5",
    )
    profile_mapping: Optional[str] = Field(
        title="profile_mapping",
        description="Profile mapping",
        default="",
        alias="Profile mapping",
    )
    is_relative_path: Optional[bool] = Field(
        title="is_relative_path",
        description="Source file path is relative",
        default=True,
    )
    settings: Optional[Dict] = Field(
        title="settings",
        description="Profiles settings",
        default={},
    )

    @root_validator(pre=True)
    def pre_process(cls, values):
        if values.get("source_type") == "HDF5":
            values["source_type"] = "h5"
        return values


class ReportBaseModel(InputsBaseModel):
    """Defines the base model for all report-specific user inputs."""

    enabled: Optional[bool] = Field(
        title="enabled",
        description="Set to true to enable the report",
        default=False,
    )
    scenarios: Optional[List[str]] = Field(
        title="scenarios",
        description="Scenarios to which the report applies. Default is all scenarios.",
        default=[],
    )
    store_all_time_points: Optional[bool] = Field(
        title="store_all_time_points",
        description="Set to true to store data for all time points. If false, store aggregated "
                    "metrics in memory.",
        default=False,
    )


class CapacitorStateChangeCountReportModel(ReportBaseModel):
    """Defines the user inputs for the Capacitor State Change Counts report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="Capacitor State Change Counts",
        internal=True,
    )


class FeederLossesReportModel(ReportBaseModel):
    """Defines the user inputs for the Feeder Losses report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="Feeder Losses",
        internal=True,
    )


class PvClippingReportModel(ReportBaseModel):
    """Defines the user inputs for the PV Clipping report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="PV Clipping",
        internal=True,
    )
    diff_tolerance_percent_pmpp: float = Field(
        title="diff_tolerance_percent_pmpp",
        description="TBD",
        default=1.0,
    )
    denominator_tolerance_percent_pmpp: float = Field(
        title="denominator_tolerance_percent_pmpp",
        description="TBD",
        default=1.0,
    )


class PvCurtailmentReportModel(ReportBaseModel):
    """Defines the user inputs for the PV Curtailment report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="PV Curtailment",
        internal=True,
    )
    diff_tolerance_percent_pmpp: Optional[float] = Field(
        title="diff_tolerance_percent_pmpp",
        description="TBD",
        default=1.0,
    )
    denominator_tolerance_percent_pmpp: Optional[float] = Field(
        title="denominator_tolerance_percent_pmpp",
        description="TBD",
        default=1.0,
    )


class RegControlTapNumberChangeCountsReportModel(ReportBaseModel):
    """Defines the user inputs for the RegControl Tap Number Change Counts report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="RegControl Tap Number Change Counts",
        internal=True,
    )


class ThermalMetricsReportModel(ReportBaseModel):
    """Defines the user inputs for the Thermal Metrics report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="Thermal Metrics",
        internal=True,
    )
    transformer_window_size_hours: Optional[int] = Field(
        title="transformer_window_size_hours",
        description="Transformer window size hours",
        default=2,
    )
    transformer_loading_percent_threshold: Optional[int] = Field(
        title="transformer_loading_percent_threshold",
        description="Transformer loading percent threshold",
        default=150,
    )
    transformer_loading_percent_moving_average_threshold: Optional[int] = Field(
        title="transformer_loading_percent_moving_average_threshold",
        description="Transformer loading percent moving average threshold",
        default=120,
    )
    line_window_size_hours: Optional[int] = Field(
        title="line_window_size_hours",
        description="Line window size hours",
        default=1,
    )
    line_loading_percent_threshold: Optional[int] = Field(
        title="line_loading_percent_threshold",
        description="Line loading percent threshold",
        default=120,
    )
    line_loading_percent_moving_average_threshold: Optional[int] = Field(
        title="line_loading_percent_moving_average_threshold",
        description="Line loading percent moving average threshold",
        default=100,
    )
    store_per_element_data: Optional[bool] = Field(
        title="store_per_element_data",
        description="Set to true to store metrics for each line and transformer.",
        default=True,
    )


class VoltageMetricsReportModel(ReportBaseModel):
    """Defines the user inputs for the Voltage Metrics report."""

    name: Optional[str] = Field(
        title="name",
        description="Report name",
        default="Voltage Metrics",
        internal=True,
    )
    window_size_minutes: Optional[int] = Field(
        title="window_size_minutes",
        description="Window size minutes",
        default=60,
    )
    range_a_limits: Optional[List] = Field(
        title="range_a_limits",
        description="ANSI Range A voltage limits",
        default=[0.95, 1.05],
    )
    range_b_limits: Optional[List] = Field(
        title="range_b_limits",
        description="ANSI Range B voltage limits",
        default=[0.90, 1.0583],
    )
    store_per_element_data: Optional[bool] = Field(
        title="store_per_element_data",
        description="Set to true to store metrics for each node.",
        default=True,
    )


_REPORT_MAPPING = {
    "Capacitor State Change Counts": CapacitorStateChangeCountReportModel,
    "Feeder Losses": FeederLossesReportModel,
    "PV Clipping": PvClippingReportModel,
    "PV Curtailment": PvCurtailmentReportModel,
    "RegControl Tap Number Change Counts": RegControlTapNumberChangeCountsReportModel,
    "Thermal Metrics": ThermalMetricsReportModel,
    "Voltage Metrics": VoltageMetricsReportModel,
}


class ReportsModel(InputsBaseModel):
    """Defines the user inputs for reports."""

    format: Optional[FileFormat] = Field(
        title="format",
        description="Controls the file format.",
        default=FileFormat.HDF5,
        alias="Format",
    )
    granularity: Optional[ReportGranularity] = Field(
        title="granularity",
        description="Specifies the granularity on which data is collected.",
        default=ReportGranularity.PER_ELEMENT_PER_TIME_POINT,
        alias="Granularity",
    )
    types: Optional[List[Any]] = Field(
        title="types",
        description="Reports to collect.",
        default=[],
        alias="Types",
    )

    @validator("types", pre=True)
    def check_types(cls, val):
        reports = []
        for report in val:
            report_cls = _REPORT_MAPPING.get(report["name"])
            if report_cls is None:
                raise ValueError(f"{report['name']} is not a valid report name")
            reports.append(report_cls(**report))

        return reports


class SimulationSettingsModel(InputsBaseModel):
    """Defines user inputs for a simulation."""

    project: ProjectModel = Field(
        title="project",
        description="Project settings",
        alias="Project",
    )
    exports: Optional[ExportsModel] = Field(
        title="exports",
        description="Exports settings",
        default=ExportsModel(),
        alias="Exports",
    )
    frequency: Optional[FrequencyModel] = Field(
        title="frequency",
        description="Frequency settings",
        default=FrequencyModel(),
        alias="Frequency",
    )
    helics: Optional[HelicsModel] = Field(
        title="helics",
        description="HELICS settings",
        default=HelicsModel(),
        alias="Helics",
    )
    logging: Optional[LoggingModel] = Field(
        title="logging",
        description="Logging settings",
        default=LoggingModel(),
        alias="Logging",
    )
    monte_carlo: Optional[MonteCarloModel] = Field(
        title="monte_carlo",
        description="Monte Carlo settings",
        default=MonteCarloModel(),
        alias="MonteCarlo",
    )
    plots: Optional[PlotsModel] = Field(
        title="plots",
        description="Plots settings",
        default=PlotsModel(),
        alias="Plots",
    )
    profiles: Optional[ProfilesModel] = Field(
        title="profiles",
        description="Profiles settings",
        default=ProfilesModel(),
        alias="Profiles",
    )
    reports: Optional[ReportsModel] = Field(
        title="reports",
        description="Reports settings",
        default=ReportsModel(),
        alias="Reports",
    )


def create_simulation_settings(path: Path, project_name: str, scenario_names: list, force=False):
    """Create a settings file with default values.

    Parameters
    ----------
    path : Path
        Path in which to create the project.
    project_name : str
        Name of the project. Will be joined with 'path'.
    scenario_names : list
        Name of each scenario to create.
    force : bool
        If project already exists, overwrite it.

    """
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        path.mkdir()
    project_path = path / project_name
    if project_path.exists():
        if force:
            shutil.rmtree(project_path)
        else:
            raise ValueError(f"{project_path} already exists. Set force=true to overwrite.")

    project_path.mkdir()
    scenarios = [ScenarioModel(name=x) for x in scenario_names]
    project = ProjectModel(
        project_path=str(path),
        active_project=project_name,
        scenarios=scenarios,
    )
    settings = SimulationSettingsModel(project=project)
    filename = project_path / SIMULATION_SETTINGS_FILENAME
    dump_settings(settings, filename)
    return filename


def dump_settings(settings: SimulationSettingsModel, filename):
    """Dump the settings into a TOML file.

    Parameters
    ----------
    settings : SimulationSettingsModel

    """
    dump_data(settings.dict(by_alias=False), filename)
    print(f"Created {filename}")


def load_simulation_settings(path: Path):
    """Load the simulation settings.

    Parameters
    ----------
    path : Path
        Path to simulation.toml

    Returns
    -------
    SimulationSettingsModel

    Raises
    ------
    ValueError
        Raised if any setting is invalid.

    """
    settings = SimulationSettingsModel(**load_data(path))
    enabled_reports = [x for x in settings.reports.types if x.enabled]
    if enabled_reports and not settings.exports.export_results:
        raise ValueError("Reports are only supported with exported_results = true.")

    return settings

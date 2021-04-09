import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

from PyDSS.utils.simulation_utils import CircularBufferHelper
from PyDSS.utils.utils import dump_data, load_data


logger = logging.getLogger(__name__)


class ThermalMetricsBaseModel(BaseModel):
    class Config:
        title = "ThermalMetricsBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False


class ThermalMetricsModel(ThermalMetricsBaseModel):
    max_instantaneous_loadings: Dict[str, float] = Field(
        title="max_instantaneous_loadings",
        description="maximum instantaneous loading percent for each element",
    )
    max_instantaneous_loading: float = Field(
        title="max_instantaneous_loading",
        description="maximum instantaneous loading percent overall",
    )
    max_moving_average_loadings: Dict[str, float] = Field(
        title="max_moving_average_loadings",
        description="maximum moving average loading percent for each element",
    )
    max_moving_average_loading: float = Field(
        title="max_moving_average_loading",
        description="maximum moving average loading percent overall",
    )
    window_size_hours: int = Field(
        title="window_size_hours",
        description="window size used to calculate the moving average",
    )
    num_time_points_with_instaneous_violations: int = Field(
        title="num_time_points_with_instaneous_violations",
        description="number of time points where the instantaneous threshold was violated",
    )
    num_time_points_with_moving_average_violations: int = Field(
        title="num_time_points_with_moving_average_violations",
        description="number of time points where the moving average threshold was violated",
    )
    instantaneous_threshold: int = Field(
        title="instantaneous_threshold",
        description="instantaneous threshold",
    )
    moving_average_threshold: int = Field(
        title="moving_average_threshold",
        description="moving average threshold",
    )


class ThermalMetricsSummaryModel(ThermalMetricsBaseModel):
    line_loadings: ThermalMetricsModel = Field(
        title="line_loadings",
        description="line loading metrics",
    )
    transformer_loadings: ThermalMetricsModel = Field(
        title="transformer_loadings",
        description="transformer loading metrics",
    )


class SimulationThermalMetricsModel(ThermalMetricsBaseModel):
    scenarios: Dict[str, ThermalMetricsSummaryModel] = Field(
        title="scenarios",
        description="thermal metrics by PyDSS scenario name",
    )


def create_summary(filename):
    """Create a summary of the metrics values for use in a table.

    Parameters
    ----------
    filename: str
        File containing a serialized SimulationThermalMetricsModel instance

    Returns
    -------
    dict
        Two-level dict. First level keys are scenario names. Second level has line/transform
        metric names and values.

    """
    data = load_data(filename)
    summary = SimulationThermalMetricsModel(**data)
    report = defaultdict(dict)
    for scenario in summary.scenarios:
        for model, elem_type in zip(("line_loadings", "transformer_loadings"), ("line", "transformer")):
            model = getattr(summary.scenarios[scenario], model)
            for column in model.fields:
                val = getattr(model, column)
                if not isinstance(val, dict):
                    new_name = elem_type + "_" + column
                    report[scenario][new_name] = val

    return report


class ThermalMetrics:
    """Stores thermal metrics in memory.

    The metrics are defined in this paper:
    https://www.sciencedirect.com/science/article/pii/S0306261920311351

    """

    FILENAME = "thermal_metrics.json"

    def __init__(
        self,
        prop,
        start_time,
        sim_resolution,
        line_window_size_hours,
        line_window_size,
        transformer_window_size_hours,
        transformer_window_size,
        line_loading_percent_threshold,
        line_loading_percent_moving_average_threshold,
        transformer_loading_percent_threshold,
        transformer_loading_percent_moving_average_threshold,
    ):
        self._prop = prop
        self._start_time = start_time
        self._resolution = sim_resolution
        self._line_window_size_hours = line_window_size_hours
        self._line_window_size = line_window_size
        self._line_loading_percent_threshold = line_loading_percent_threshold
        self._line_loading_percent_mavg_threshold = line_loading_percent_moving_average_threshold
        self._transformer_loading_percent_threshold = transformer_loading_percent_threshold
        self._transformer_window_size_hours = transformer_window_size_hours
        self._transformer_window_size = transformer_window_size
        self._transformer_loading_percent_mavg_threshold = transformer_loading_percent_moving_average_threshold
        self._num_time_points_inst_line_violations = 0
        self._num_time_points_mavg_line_violations = 0
        self._num_time_points_inst_transformer_violations = 0
        self._num_time_points_mavg_transformer_violations = 0
        self._max_inst_line_violations = None
        self._max_mavg_line_violations = None
        self._max_inst_transformer_violations = None
        self._max_mavg_transformer_violations = None
        self._line_bufs = None
        self._transformer_bufs = None
        self._num_time_points = 0
        self._line_names = None
        self._transformer_names = None

    def generate_report(self, path):
        """Create a summary file containing all metrics.

        Parameters
        ----------
        path : str

        Returns
        -------
        str
            report filename

        """
        if self._num_time_points == 0:
            logger.error("Cannot generate report with no time points")
            return

        inst_violations_by_line = {}
        mavg_violations_by_line = {}
        for i in range(len(self._max_inst_line_violations)):
            inst_violations_by_line[self._line_names[i]] = self._max_inst_line_violations[i]
        for i in range(len(self._max_mavg_line_violations)):
            mavg_violations_by_line[self._line_names[i]] = self._max_mavg_line_violations[i]
        line_metric = ThermalMetricsModel(
            max_instantaneous_loadings=inst_violations_by_line,
            max_instantaneous_loading=max(inst_violations_by_line.values()),
            max_moving_average_loadings=mavg_violations_by_line,
            max_moving_average_loading=max(mavg_violations_by_line.values()),
            window_size_hours=self._line_window_size_hours,
            num_time_points_with_instaneous_violations=self._num_time_points_inst_line_violations,
            num_time_points_with_moving_average_violations=self._num_time_points_mavg_line_violations,
            instantaneous_threshold=self._line_loading_percent_threshold,
            moving_average_threshold=self._line_loading_percent_mavg_threshold,
        )

        inst_violations_by_transformer = {}
        mavg_violations_by_transformer = {}
        for i in range(len(self._max_inst_transformer_violations)):
            inst_violations_by_transformer[self._transformer_names[i]] = self._max_inst_transformer_violations[i]
        for i in range(len(self._max_mavg_transformer_violations)):
            mavg_violations_by_transformer[self._transformer_names[i]] = self._max_mavg_transformer_violations[i]

        transformer_metric = ThermalMetricsModel(
            max_instantaneous_loadings=inst_violations_by_transformer,
            max_instantaneous_loading=max(inst_violations_by_transformer.values()),
            max_moving_average_loadings=mavg_violations_by_transformer,
            max_moving_average_loading=max(mavg_violations_by_transformer.values()),
            window_size_hours=self._transformer_window_size_hours,
            num_time_points_with_instaneous_violations=self._num_time_points_inst_transformer_violations,
            num_time_points_with_moving_average_violations=self._num_time_points_mavg_transformer_violations,
            instantaneous_threshold=self._transformer_loading_percent_threshold,
            moving_average_threshold=self._transformer_loading_percent_mavg_threshold,
        )

        summary = ThermalMetricsSummaryModel(
            line_loadings=line_metric,
            transformer_loadings=transformer_metric,
        )

        filename = os.path.join(path, "thermal_metrics.json")
        with open(filename, "w") as f_out:
            f_out.write(summary.json(indent=2))
            f_out.write("\n")
        logger.info("Generated thermal metric report in %s", filename)

    @property
    def line_names(self):
        return self._line_names

    @property
    def transformer_names(self):
        return self._transformer_names

    @line_names.setter
    def line_names(self, names):
        self._line_names = names

    @transformer_names.setter
    def transformer_names(self, names):
        self._transformer_names = names

    def increment_steps(self):
        """Increment the time step counter."""
        self._num_time_points += 1

    def update(self, time_step, line_loadings, transformer_loadings):
        """Update the metrics for the time step.

        Parameters
        ----------
        time_step : int
        voltages : list
            list of ValueStorageBase

        """
        if self._line_bufs is None:
            self._line_bufs = [CircularBufferHelper(self._line_window_size)] * len(
                self._line_names
            )
            self._transformer_bufs = [CircularBufferHelper(self._transformer_window_size)] * len(
                self._transformer_names
            )
            self._max_inst_line_violations = [0.0] * len(self._line_names)
            self._max_mavg_line_violations = [0.0] * len(self._line_names)
            self._max_inst_transformer_violations = [0.0] * len(self._transformer_names)
            self._max_mavg_transformer_violations = [0.0] * len(self._transformer_names)

        has_inst_line_violation = False
        has_mavg_line_violation = False
        for i, loading in enumerate(line_loadings):
            if loading.value > self._max_inst_line_violations[i]:
                self._max_inst_line_violations[i] = loading.value
            if not has_inst_line_violation and loading.value > self._line_loading_percent_threshold:
                has_inst_line_violation = True

            buf = self._line_bufs[i]
            buf.append(loading.value)
            moving_avg = buf.average()
            if moving_avg > self._max_mavg_line_violations[i]:
                self._max_mavg_line_violations[i] = moving_avg
            if not has_mavg_line_violation and moving_avg > self._line_loading_percent_mavg_threshold:
                has_mavg_line_violation = True

        has_inst_transformer_violation = False
        has_mavg_transformer_violation = False
        for i, loading in enumerate(transformer_loadings):
            if loading.value > self._max_inst_transformer_violations[i]:
                self._max_inst_transformer_violations[i] = loading.value
            if not has_inst_transformer_violation and loading.value > self._transformer_loading_percent_threshold:
                has_inst_transformer_violation = True

            buf = self._transformer_bufs[i]
            buf.append(loading.value)
            moving_avg = buf.average()
            if moving_avg > self._max_mavg_transformer_violations[i]:
                self._max_mavg_transformer_violations[i] = moving_avg
            if not has_mavg_transformer_violation and moving_avg > self._transformer_loading_percent_mavg_threshold:
                has_mavg_transformer_violation = True

        if has_inst_line_violation:
            self._num_time_points_inst_line_violations += 1
        if has_mavg_line_violation:
            self._num_time_points_mavg_line_violations += 1
        if has_inst_transformer_violation:
            self._num_time_points_inst_transformer_violations += 1
        if has_mavg_transformer_violation:
            self._num_time_points_mavg_transformer_violations += 1

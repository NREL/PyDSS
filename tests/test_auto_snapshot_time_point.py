
import datetime
import logging
import math
import os
import re
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from PyDSS.common import SIMULATION_SETTINGS_FILENAME
from PyDSS.node_voltage_metrics import SimulationVoltageMetricsModel, compare_voltage_metrics
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from PyDSS.reports.feeder_losses import SimulationFeederLossesMetricsModel, compare_feeder_losses
from PyDSS.reports.reports import ReportGranularity
from PyDSS.thermal_metrics import SimulationThermalMetricsModel, compare_thermal_metrics
from PyDSS.utils.dataframe_utils import read_dataframe
from PyDSS.utils.utils import load_data, dump_data
from tests.common import AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH, cleanup_project


logger = logging.getLogger(__name__)


def test_auto_snapshot_time_point(cleanup_project):
    PyDssProject.run_project(
        AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )
    project = PyDssProject.load_project(AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH)
    settings = project.read_scenario_time_settings("max_pv_load_ratio")
    assert str(settings["start_time"]) == "2020-01-01 11:15:00"

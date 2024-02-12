import logging

from tests.common import AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH, cleanup_project
from PyDSS.common import SIMULATION_SETTINGS_FILENAME
from PyDSS.pydss_project import PyDssProject

logger = logging.getLogger(__name__)


def test_auto_snapshot_time_point(cleanup_project):
    PyDssProject.run_project(
        AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )
    project = PyDssProject.load_project(AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH)
    settings = project.read_scenario_time_settings("max_pv_load_ratio")
    assert str(settings["start_time"]) == "2020-01-01 11:15:00"

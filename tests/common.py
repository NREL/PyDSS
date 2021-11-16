
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import opendssdirect as dss
import pytest

from PyDSS.common import PROJECT_TAR, PROJECT_ZIP, RUN_SIMULATION_FILENAME
from PyDSS.pydss_fs_interface import STORE_FILENAME
from PyDSS.pydss_project import PyDssProject
from PyDSS.utils.utils import dump_data


RUN_PROJECT_PATH = os.path.join("tests", "data", "project")
CUSTOM_EXPORTS_PROJECT_PATH = os.path.join(
    "tests", "data", "custom_exports_project"
)
PV_REPORTS_PROJECT_PATH = os.path.join(
    "tests", "data", "pv_reports_project"
)
PV_REPORTS_PROJECT_STORE_ALL_PATH = os.path.join(
    "tests", "data", "pv_reports_project_store_all"
)
AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH = os.path.join(
    "tests", "data", "auto_snapshot_time_point_project"
)

AUTOMATED_UPGRADES_PROJECT_PATH = os.path.join(
    "tests", "data", "automated_upgrades_project")

EDLIFO_PROJECT_PATH = os.path.join(
    "tests", "data", "edlifo-project")

SCENARIO_NAME = "scenario1"


class FakeElement:
    """Fake that behaves like an OpenDSS element"""
    def __init__(self, full_name, name):
        self.FullName = full_name
        self.Name = NameError
        self._Class = dss.PVsystems


@pytest.fixture
def cleanup_project():
    projects = (
        RUN_PROJECT_PATH,
        CUSTOM_EXPORTS_PROJECT_PATH,
        PV_REPORTS_PROJECT_PATH,
        PV_REPORTS_PROJECT_STORE_ALL_PATH,
        EDLIFO_PROJECT_PATH,
        AUTO_SNAPSHOT_TIME_POINT_PROJECT_PATH,
    )
    for project_path in projects:
        export_path = os.path.join(project_path, "Exports")
        reports_path = os.path.join(project_path, "Reports")
        logs_path = os.path.join(project_path, "Logs")
        for path in (logs_path, export_path, reports_path):
            os.makedirs(path, exist_ok=True)

    yield

    for project_path in projects:
        orig = os.getcwd()
        try:
            os.chdir(project_path)
            if os.path.exists(PROJECT_TAR):
                with tarfile.open(PROJECT_TAR) as tar:
                    tar.extractall()
                os.remove(PROJECT_TAR)
                pass
            elif os.path.exists(PROJECT_ZIP):
                with zipfile.ZipFile(PROJECT_ZIP) as zipf:
                    zipf.extractall()
                os.remove(PROJECT_ZIP)
                pass
        finally:
            os.chdir(orig)

        export_path = os.path.join(project_path, "Exports")
        reports_path = os.path.join(project_path, "Reports")
        logs_path = os.path.join(project_path, "Logs")
        for path in (logs_path, export_path, reports_path):
            if os.path.exists(path):
                os.chmod(path, 0o777)
                shutil.rmtree(path)
            os.mkdir(path)

        store_filename = os.path.join(project_path, STORE_FILENAME)
        if os.path.exists(store_filename):
            os.remove(store_filename)

        for path in Path(project_path).rglob(RUN_SIMULATION_FILENAME):
            os.remove(path)


def run_project_with_custom_exports(path, scenario, sim_file, data):
    """Runs a project while overriding an export config file."""
    exports = f"{path}/Scenarios/{scenario}/ExportLists/Exports.toml"
    backup = exports + ".bk"
    shutil.copyfile(exports, backup)
    dump_data(data, exports)

    try:
        PyDssProject.run_project(path, simulation_file=sim_file)
    finally:
        os.remove(exports)
        os.rename(backup, exports)

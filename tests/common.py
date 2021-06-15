
import os
import shutil
import tarfile
import zipfile

import pytest

from PyDSS.common import PROJECT_TAR, PROJECT_ZIP
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
SCENARIO_NAME = "scenario1"


@pytest.fixture
def cleanup_project():
    for project_path in (RUN_PROJECT_PATH, CUSTOM_EXPORTS_PROJECT_PATH):
        export_path = os.path.join(project_path, "Exports", "scenario1")
        logs_path = os.path.join(project_path, "Logs")
        for path in (logs_path, export_path):
            os.makedirs(path, exist_ok=True)

    yield

    for project_path in (RUN_PROJECT_PATH, CUSTOM_EXPORTS_PROJECT_PATH):
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

        for path in (logs_path, export_path):
            if os.path.exists(path):
                os.chmod(path, 0o777)
                shutil.rmtree(path)
                pass
            os.mkdir(path)

        store_filename = os.path.join(project_path, STORE_FILENAME)
        if os.path.exists(store_filename):
            os.remove(store_filename)
            pass

        scenario_config_file = os.path.join(
            project_path, "Scenarios", "scenario1", "simulation-run.toml"
        )
        if os.path.exists(scenario_config_file):
            os.remove(scenario_config_file)
            pass


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

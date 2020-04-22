
import os
import shutil
import tarfile
import zipfile

import pytest

from PyDSS.common import PROJECT_TAR, PROJECT_ZIP
from PyDSS.pydss_fs_interface import STORE_FILENAME


RUN_PROJECT_PATH = os.path.join("tests", "data", "project")
SCENARIO_NAME = "scenario1"


@pytest.fixture
def cleanup_project():
    export_path = os.path.join(RUN_PROJECT_PATH, "Exports", "scenario1")
    logs_path = os.path.join(RUN_PROJECT_PATH, "Logs")
    for path in (logs_path, export_path):
        os.makedirs(path, exist_ok=True)

    yield

    orig = os.getcwd()
    try:
        os.chdir(RUN_PROJECT_PATH)
        if os.path.exists(PROJECT_TAR):
            with tarfile.open(PROJECT_TAR) as tar:
                tar.extractall()
            os.remove(PROJECT_TAR)
        elif os.path.exists(PROJECT_ZIP):
            with zipfile.ZipFile(PROJECT_ZIP) as zipf:
                zipf.extractall()
            os.remove(PROJECT_ZIP)
    finally:
        os.chdir(orig)

    for path in (logs_path, export_path):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)

    store_filename = os.path.join(RUN_PROJECT_PATH, STORE_FILENAME)
    if os.path.exists(store_filename):
        os.remove(store_filename)

    scenario_config_file = os.path.join(
        RUN_PROJECT_PATH, "Scenarios", "scenario1", "simulation-run.toml"
    )
    if os.path.exists(scenario_config_file):
        os.remove(scenario_config_file)

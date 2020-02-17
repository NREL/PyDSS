
import os
import shutil

import pytest


RUN_PROJECT_PATH = os.path.join("tests", "data", "project")
SCENARIO_NAME = "scenario1"


@pytest.fixture
def cleanup_project():
    yield
    export_path = os.path.join(RUN_PROJECT_PATH, "Exports", "scenario1")
    logs_path = os.path.join(RUN_PROJECT_PATH, "Logs")
    for path in (logs_path, export_path):
        shutil.rmtree(path)
        os.mkdir(path)


import os
import shutil
import tempfile

import pytest

from PyDSS.pydss_project import PyDssProject, PyDssScenario


PATH = os.path.join(tempfile.gettempdir(), "pydss-projects")


@pytest.fixture
def pydss_project():
    if os.path.exists(PATH):
        shutil.rmtree(PATH)
    yield
    if os.path.exists(PATH):
        shutil.rmtree(PATH)


def test_create_project(pydss_project):
    project_name = "test-project"
    project_dir = os.path.join(PATH, project_name)
    scenarios = [PyDssScenario(x) for x in ("scenario1", "scenario2")]
    project = PyDssProject.create_project(PATH, project_name, scenarios)
    assert os.path.exists(project_dir)
    for dir_name in PyDssScenario._SCENARIO_DIRECTORIES:
        for scenario in scenarios:
            path = os.path.join(
                project_dir,
                PyDssProject._SCENARIOS,
                scenario.name,
                dir_name,
            )
            assert os.path.exists(path)

    project2 = PyDssProject.load_project(project_dir)
    assert project.name == project2.name
    scenarios1 = project.scenarios
    scenarios1.sort(key=lambda x: x.name)
    scenarios2 = project2.scenarios
    scenarios2.sort(key=lambda x: x.name)

    assert len(scenarios1) == len(scenarios2)
    for i in range(len(project.scenarios)):
        assert scenarios1[i].name == scenarios2[i].name
        assert scenarios1[i].controllers == scenarios2[i].controllers
        assert scenarios1[i].plots == scenarios2[i].plots

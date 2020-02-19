
import copy
import os

from tests.common import RUN_PROJECT_PATH, SCENARIO_NAME, cleanup_project
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults


OPTIONS = {
    "Project": {
        "Simulation Type": "Snapshot",
    },
    "Exports": {
        "Export Iteration Order": "ValuesByPropertyAcrossElements",
        "Export Format": "csv",
        "Export Compression": True,
    },
}

def test_export_compression(cleanup_project):
    values = (
        (True, "Lines__Currents.csv.gz"),
        (False, "Lines__Currents.csv"),
    )
    for enable_compression, filename in values:
        options = copy.deepcopy(OPTIONS)
        options["Exports"]["Export Compression"] = enable_compression
        PyDssProject.run_project(RUN_PROJECT_PATH, options=options)
        project = PyDssProject.load_project(RUN_PROJECT_PATH)
        export_path = project.export_path(SCENARIO_NAME)
        expected = os.path.join(export_path, filename)
        assert os.path.exists(expected)


def test_export_h5(cleanup_project):
    for enable_compression in (True, False):
        options = copy.deepcopy(OPTIONS)
        options["Exports"]["Export Format"] = "h5"
        options["Exports"]["Export Compression"] = enable_compression
        PyDssProject.run_project(RUN_PROJECT_PATH, options=options)
        project = PyDssProject.load_project(RUN_PROJECT_PATH)
        export_path = project.export_path(SCENARIO_NAME)
        expected = os.path.join(export_path, "Lines__Currents.h5")
        assert os.path.exists(expected)

        results = PyDssResults(RUN_PROJECT_PATH)
        assert len(results.scenarios) == 1
        scenario = results.scenarios[0]
        names = scenario.list_element_names("Lines", "Currents")
        df = scenario.get_dataframe("Lines", "Currents", names[1], phase_terminal="A1")
        assert len(df) == 1
        start = df.index[0].timetuple()
        assert start.tm_year == project.simulation_config["Project"]["Start Year"]
        assert start.tm_yday == project.simulation_config["Project"]["Start Day"]

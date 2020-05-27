
import datetime
import os
import re
import shutil
import tempfile

import pandas as pd

from PyDSS.utils.utils import load_data
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from tests.common import CUSTOM_EXPORTS_PROJECT_PATH, cleanup_project
from PyDSS.common import SIMULATION_SETTINGS_FILENAME


def test_custom_exports(cleanup_project):
    PyDssProject.run_project(
        CUSTOM_EXPORTS_PROJECT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )
    results = PyDssResults(CUSTOM_EXPORTS_PROJECT_PATH)
    assert len(results.scenarios) == 1
    scenario = results.scenarios[0]

    # Property stored at all time points.
    df = scenario.get_full_dataframe("Buses", "puVmagAngle")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 96

    # Filtered value on custom function.
    df = scenario.get_dataframe("Lines", "LoadingPercent", "Line.pvl_110")
    assert len(df) < 96

    # Subset of names. VoltagesMagAng has specific names, CurrentsMagAng has regex
    for name in ("Line.pvl_110", "Line.pvl_111", "Line.pvl_112", "Line.pvl_113"):
        properties = scenario.list_element_properties("Lines", element_name=name)
        assert "VoltagesMagAng" in properties
        assert "CurrentsMagAng" in properties

    properties  = scenario.list_element_properties("Lines", element_name="Line.SL_14")
    assert "VoltagesMagAng" not in properties
    assert "CurrentsMagAng" not in properties

    # Two types of sums are stored.
    normal_amps_sum = scenario.get_element_property_sum("Lines", "NormalAmpsSum", "Line.pvl_110")
    assert normal_amps_sum == 96 * 65.0
    scenario.get_element_property_sum("Lines", "CurrentsSum", "Line.pvl_110")

    sums_json = os.path.join(
        CUSTOM_EXPORTS_PROJECT_PATH,
        "Exports",
        "scenario1",
        "element_property_sums.json"
    )
    assert os.path.exists(sums_json)
    data = load_data(sums_json)
    assert data

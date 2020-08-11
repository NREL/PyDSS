
import datetime
import os
import re
import shutil
import tempfile

import pandas as pd

from PyDSS.utils.utils import load_data, dump_data
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from tests.common import PV_REPORTS_PROJECT_PATH, cleanup_project
from PyDSS.common import SIMULATION_SETTINGS_FILENAME


def test_pv_reports(cleanup_project):
    PyDssProject.run_project(
        PV_REPORTS_PROJECT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )
    results = PyDssResults(PV_REPORTS_PROJECT_PATH)

    # This test data doesn't have changes for Capacitors or RegControls.
    capacitor_change_counts = results.read_report("Capacitor State Change Counts")
    assert len(capacitor_change_counts["scenarios"]) == 2
    assert not capacitor_change_counts["scenarios"][1]["capacitors"]

    reg_control_change_counts = results.read_report("RegControl Tap Number Change Counts")
    assert len(reg_control_change_counts["scenarios"]) == 2
    assert not reg_control_change_counts["scenarios"][1]["reg_controls"]

    pv_clipping = results.read_report("PV Clipping")
    assert len(pv_clipping["pv_systems"]) == 5
    for pv_system in pv_clipping["pv_systems"]:
        assert "pv_clipping" in pv_system

    pv_curtailment = results.read_report("PV Curtailment")
    assert isinstance(pv_curtailment, pd.DataFrame)

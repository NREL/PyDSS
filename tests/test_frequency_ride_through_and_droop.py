import re
import os
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from tests.common import (
    FREQUENCY_RIDE_THROUGH_AND_DROOP_PATH,
    cleanup_project
)
from PyDSS.common import (SIMULATION_SETTINGS_FILENAME,
                          RUN_SIMULATION_FILENAME,
)
from PyDSS.pydss_fs_interface import STORE_FILENAME

def test_frt_and_droop(cleanup_project):
    PyDssProject.run_project(
        path=FREQUENCY_RIDE_THROUGH_AND_DROOP_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME
    )
    results=PyDssResults(FREQUENCY_RIDE_THROUGH_AND_DROOP_PATH)
    scenario_droop=results.scenarios[0]
    scenario_frt=results.scenarios[1]

    kw_df_droop=scenario_droop.get_full_dataframe("Generators", "kW")
    class_df_droop=scenario_droop.get_full_dataframe("Generators", "class")
    kw_df_frt=scenario_frt.get_full_dataframe("Generators", "kW")
    class_df_frt=scenario_frt.get_full_dataframe("Generators", "class")
    
    assert not kw_df_droop[kw_df_droop[kw_df_droop.columns[0]]<=8].empty
    assert 0.0 in kw_df_frt.values
    assert 1.0 not in class_df_droop.values
    assert 1.0 in class_df_frt.values
        
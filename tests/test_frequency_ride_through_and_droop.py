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
    print('HERE')
    PyDssProject.run_project(
        path=FREQUENCY_RIDE_THROUGH_AND_DROOP_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME
    )
    results=PyDssResults(FREQUENCY_RIDE_THROUGH_AND_DROOP_PATH)
    scenario_droop=results.scenarios[0]

    # kw_df_FRT=scenario_FRT.get_full_dataframe("Generators", "kW")
    kw_df_droop=scenario_droop.get_full_dataframe("Generators", "kW")
    # class_df_FRT=scenario_FRT.get_full_dataframe("Generators", "class")
    class_df_droop=scenario_droop.get_full_dataframe("Generators", "class")
    
    # initial_kw_FRT=kw_df_FRT.iloc[0][kw_df_FRT.columns[0]]
    # last_kw_FRT=kw_df_FRT.iloc[-1][kw_df_FRT.columns[0]]

    initial_kw_droop=kw_df_droop.iloc[0][kw_df_droop.columns[0]]
    last_kw_droop=kw_df_droop.iloc[-1][kw_df_droop.columns[0]]

    # print('kw_df_FRT:',kw_df_FRT)
    print('kw_df_droop:',kw_df_droop)

    # print('class_df_FRT:',class_df_FRT)
    print('class_df_droop:',class_df_droop)

    # print('initial_kw_FRT:',initial_kw_FRT)
    # print('last_kw_FRT:',last_kw_FRT)

    print('initial_kw_droop:',initial_kw_droop)
    print('last_kw_droop:',last_kw_droop)

    assert not kw_df_droop[kw_df_droop[kw_df_droop.columns[0]]<=8].empty
    assert not kw_df_droop[kw_df_droop[kw_df_droop.columns[0]]<=8].empty
    # assert initial_kvar_DVS_only == last_kvar_DVS_only #check that it returns values to their original state after fault has cleared in DVS only
    
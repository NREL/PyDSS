import re
import os
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from tests.common import (
    DYNAMIC_VOLTAGE_SUPPORT_PATH,
    cleanup_project
)
from PyDSS.common import (SIMULATION_SETTINGS_FILENAME,
                          RUN_SIMULATION_FILENAME,
)
from PyDSS.pydss_fs_interface import STORE_FILENAME

def test_dynamic_voltage_support(cleanup_project):
    PyDssProject.run_project(
        path=DYNAMIC_VOLTAGE_SUPPORT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME
    )
    results=PyDssResults(DYNAMIC_VOLTAGE_SUPPORT_PATH)
    scenario_DVS_only=results.scenarios[0] #DVS Only
    scenario_no_vrt=results.scenarios[1] #DVS and VRT with instantaneous trip
    scenario_vrt=results.scenarios[2] #DVS with 1547 VRT

    kvar_df=scenario_DVS_only.get_full_dataframe("Generators", "kvar") #var from DVS only scenario
    kvar_df_vrt=scenario_vrt.get_full_dataframe("Generators", "kvar") #kvar from DVS + VRT scenario
    class_df_no_vrt=scenario_no_vrt.get_full_dataframe("Generators", "class")# class from DVS + instantaneous trip
    class_df_vrt=scenario_vrt.get_full_dataframe("Generators", "class") #class from  DVS + 1547 VRT
    
    initial_kvar_DVS_only=kvar_df.iloc[0][kvar_df.columns[0]] #initial kvar value DVS only
    last_kvar_DVS_only=kvar_df.iloc[-1][kvar_df.columns[0]] #final kvar value DVS only

    initial_kvar_VRT=kvar_df_vrt.iloc[0][kvar_df_vrt.columns[0]]#initial kvar value DVS + IEEE 1547 VRT
    last_kvar_VRT=kvar_df_vrt.iloc[-1][kvar_df_vrt.columns[0]]#final kvar value DVS + IEEE 1547 VRT

    assert not kvar_df[kvar_df[kvar_df.columns[0]]!=initial_kvar_DVS_only].empty #check that controller changes generator kvar values in DVS only
    assert initial_kvar_DVS_only == last_kvar_DVS_only #check that it returns values to their original state after fault has cleared in DVS only
    
    assert 1.0 in class_df_no_vrt[class_df_no_vrt.columns[0]].unique() #check that generator trips offline in DVS + instantaneous trip
    assert 1.0 not in class_df_vrt[class_df_vrt.columns[0]].unique() #check that generator rides through in DVS + instantaneous trip
    
    assert not kvar_df_vrt[kvar_df_vrt[kvar_df_vrt.columns[0]]!=initial_kvar_VRT].empty #check that controller changes generator kvar values in DVS + 1547 VRT
    assert initial_kvar_VRT == last_kvar_VRT #check that it returns values to their original state after fault has cleared in DVS + 1547 VRT
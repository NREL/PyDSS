from PyDSS.utils.simulation_utils import create_loadshape_pmult_dataframe_for_simulation
from PyDSS.reports.reports import logger
import pandas as pd


def get_snapshot_timepoint(dss, options):
    pv_systems = dss.PVsystems.AllNames()
    if not pv_systems:
        logger.info("No PVSystems are present")
    pv_profiles_df = pd.DataFrame()
    for pv_name in pv_systems:
        dss.PVsystems.Name(pv_name)
        pmpp = float(dss.Properties.Value('Pmpp'))
        profile_name = dss.Properties.Value('yearly')
        dss.LoadShape.Name(profile_name)
        pv_profiles_df[pv_name] = create_loadshape_pmult_dataframe_for_simulation(options) * pmpp

    loads = dss.Loads.AllNames()
    if not loads:
        logger.info("No Loads are present")
    load_profiles_df = pd.DataFrame()
    for load_name in loads:
        dss.Loads.Name(load_name)
        kw = float(dss.Properties.Value('kW'))
        profile_name = dss.Properties.Value('yearly')
        dss.LoadShape.Name(profile_name)
        load_profiles_df[load_name] = create_loadshape_pmult_dataframe_for_simulation(options) * kw

    aggregate_profiles = pd.DataFrame()
    aggregate_profiles['Load'] = load_profiles_df.sum(axis=1)
    aggregate_profiles['PV'] = pv_profiles_df.sum(axis=1)
    aggregate_profiles['PV to Load Ratio'] = aggregate_profiles['PV'] / aggregate_profiles['Load']
    aggregate_profiles['PV-Load'] = aggregate_profiles['PV'] - aggregate_profiles['Load']

    timepoints = pd.DataFrame({'Timepoints': aggregate_profiles.idxmax().T})
    timepoints.index = 'Max ' + timepoints.index
    timepoints.loc['Min Load'] = aggregate_profiles['Load'].idxmin()
    return timepoints


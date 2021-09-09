"""Logic to determine snapshot time point by mode"""

import logging

from PyDSS.common import SnapshotTimePointSelectionMode
from PyDSS.utils.simulation_utils import create_loadshape_pmult_dataframe_for_simulation
from PyDSS.reports.reports import logger

import pandas as pd
import opendssdirect as dss


logger = logging.getLogger(__name__)


def get_snapshot_timepoint(options, mode: SnapshotTimePointSelectionMode):
    pv_generation_hours = {'start_time': '8:00', 'end_time': '17:00'}
    pv_systems = dss.PVsystems.AllNames()
    if not pv_systems:
        logger.info("No PVSystems are present.")
        if mode != SnapshotTimePointSelectionMode.MAX_LOAD:
            mode = SnapshotTimePointSelectionMode.MAX_LOAD
            logger.info("Changed mode to %s", SnapshotTimePointSelectionMode.MAX_LOAD.value)
    pv_profiles = {}
    index = None
    for pv_name in pv_systems:
        dss.PVsystems.Name(pv_name)
        pmpp = float(dss.Properties.Value('Pmpp'))
        profile_name = dss.Properties.Value('yearly')
        dss.LoadShape.Name(profile_name)
        df = create_loadshape_pmult_dataframe_for_simulation(options) * pmpp
        if index is None:
            index = df.index
        pv_profiles[pv_name] = df.values[:, 0]
    pv_profiles_df = pd.DataFrame(pv_profiles, index=index)

    loads = dss.Loads.AllNames()
    if not loads:
        logger.info("No Loads are present")
    load_profiles = {}
    for load_name in loads:
        dss.Loads.Name(load_name)
        kw = float(dss.Properties.Value('kW'))
        profile_name = dss.Properties.Value('yearly')
        dss.LoadShape.Name(profile_name)
        df = create_loadshape_pmult_dataframe_for_simulation(options) * kw
        if index is None:
            index = df.index
        load_profiles[load_name] = df.values[:, 0]
    load_profiles_df = pd.DataFrame(load_profiles, index=index)

    aggregate_profiles = pd.DataFrame()
    aggregate_profiles['Load'] = load_profiles_df.sum(axis=1)
    if pv_systems:
        aggregate_profiles['PV'] = pv_profiles_df.sum(axis=1)
        aggregate_profiles['PV to Load Ratio'] = aggregate_profiles['PV'] / aggregate_profiles['Load']
        aggregate_profiles['PV minus Load'] = aggregate_profiles['PV'] - aggregate_profiles['Load']

    timepoints = pd.DataFrame(columns=['Timepoints'])
    timepoints.loc['Max Load'] = aggregate_profiles['Load'].idxmax()
    if pv_systems:
        timepoints.loc['Max PV to Load Ratio'] = aggregate_profiles.between_time(pv_generation_hours['start_time'],
                                                                                 pv_generation_hours['end_time'])['PV to Load Ratio'].idxmax()
        timepoints.loc['Max PV minus Load'] = aggregate_profiles.between_time(pv_generation_hours['start_time'],
                                                                              pv_generation_hours['end_time'])['PV minus Load'].idxmax()
        timepoints.loc['Max PV'] = aggregate_profiles.between_time(pv_generation_hours['start_time'],
                                                                   pv_generation_hours['end_time'])['PV'].idxmax()
    timepoints.loc['Min Load'] = aggregate_profiles['Load'].idxmin()
    timepoints.loc['Min Daytime Load'] = aggregate_profiles.between_time(pv_generation_hours['start_time'],
                                                                         pv_generation_hours['end_time'])['Load'].idxmin()
    logger.info("Time points: %s", {k: str(v) for k, v in timepoints.to_records()})
    if mode == SnapshotTimePointSelectionMode.MAX_LOAD:
        column = "Max Load"
    elif mode == SnapshotTimePointSelectionMode.MAX_PV_LOAD_RATIO:
        column = "Max PV to Load Ratio"
    elif mode == SnapshotTimePointSelectionMode.DAYTIME_MIN_LOAD:
        column = "Min Daytime Load"
    elif mode == SnapshotTimePointSelectionMode.MAX_PV_MINUS_LOAD:
        column = "Max PV minus Load"
    else:
        assert False, f"{mode} is not supported"
    return timepoints.loc[column][0].to_pydatetime()

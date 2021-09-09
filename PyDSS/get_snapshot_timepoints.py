"""Logic to determine snapshot time point by mode"""

import logging

from PyDSS.common import SimulationTimeMode
from PyDSS.utils.simulation_utils import create_loadshape_pmult_dataframe_for_simulation
from PyDSS.reports.reports import logger

import pandas as pd
import opendssdirect as dss


logger = logging.getLogger(__name__)


def get_snapshot_timepoint(options, mode: SimulationTimeMode):
    daytime_hours = {'start_time': '6:30', 'end_time': '18:00'}
    pv_systems = dss.PVsystems.AllNames()
    if not pv_systems:
        logger.info("No PVSystems are present. Max loading condition is chosen by default.")
        if mode != SimulationTimeMode.MAX_LOAD:
            mode = SimulationTimeMode.MAX_LOAD
            logger.info("Changed mode to %s", SimulationTimeMode.MAX_LOAD.value)
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
        load_profiles[load_name] = df.values[:, 0]
    load_profiles_df = pd.DataFrame(load_profiles, index=index)

    aggregate_profiles = pd.DataFrame()
    aggregate_profiles['Load'] = load_profiles_df.sum(axis=1)
    aggregate_profiles['PV'] = pv_profiles_df.sum(axis=1)
    aggregate_profiles['PV to Load Ratio'] = aggregate_profiles['PV'] / aggregate_profiles['Load']
    aggregate_profiles['PV minus Load'] = aggregate_profiles['PV'] - aggregate_profiles['Load']

    timepoints = pd.DataFrame({'Timepoints': aggregate_profiles.idxmax().T})
    timepoints.index = 'Max ' + timepoints.index
    timepoints.loc['Min Load'] = aggregate_profiles['Load'].idxmin()
    timepoints.loc['Min Daytime Load'] = aggregate_profiles.between_time(daytime_hours['start_time'],
                                                                         daytime_hours['end_time'])['Load'].idxmin()

    logger.info("Time points: %s", {k: str(v) for k, v in timepoints.to_records()})

    if mode == SimulationTimeMode.MAX_LOAD:
        column = "Max Load"
    elif mode == SimulationTimeMode.MAX_PV_LOAD_RATIO:
        column = "Max PV to Load Ratio"
    else:
        assert False, f"{mode} is not supported"
    return timepoints.loc[column][0].to_pydatetime()

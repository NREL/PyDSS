from PyDSS.common import DATE_FORMAT
from datetime import datetime
import enum
import os

import toml

from PyDSS.exceptions import InvalidConfiguration
from PyDSS.common import SnapshotTimePointSelectionMode
from PyDSS.reports.reports import ReportGranularity
from PyDSS.utils.utils import TomlEnumEncoder


settings_dict = {
        "Exports": {
            'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
            'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},
            # Feather is not supported because its underlying libraries do not support complex numbers
            'Export Format': {'type': str, 'Options': ["csv", "h5"]},
            'Export Compression': {'type': bool, 'Options': [True, False]},
            'Export Elements': {'type': bool, 'Options': [True, False]},
            'Export Element Types': {'type': list},
            'Export Event Log': {'type': bool, 'Options': [True, False]},
            'Export Data Tables': {'type': bool, 'Options': [True, False]},
            'Export Data In Memory': {'type': bool, 'Options': [True, False]},
            'Export Node Names By Type': {'type': bool, 'Options': [True, False]},
            'HDF Max Chunk Bytes': {'type': int, 'Options': range(16 * 1024, 1024 * 1024 + 1)},
            'Export PV Profiles': {'type': bool, 'Options': [True, False]},
            'Log Results': {'type': bool, 'Options': [True, False]},
        },
        "Frequency": {
            'Enable frequency sweep': {'type': bool, 'Options': [True, False]},
            'Fundamental frequency': {'type': int, 'Options': [50, 60]},
            'Start frequency': {'type': float},
            'End frequency': {'type': float},
            'frequency increment': {'type': float},
            'Neglect shunt admittance': {'type': bool, 'Options': [True, False]},
            'Percentage load in series': {'type': float, 'Options': range(0, 100)},
        },
        "Helics": {
            'Co-simulation Mode': {'type': bool, 'Options': [True, False]},
            'Iterative Mode': {'type': bool, 'Options': [True, False]},
            'Max co-iterations': {'type': int, 'Options': range(1, 1000)},
            'Error tolerance': {'type': float},
            'Federate name': {'type': str},
            'Broker': {'type': str},
            'Broker port': {'type': int},
            'Time delta': {'type': float},
            'Core type': {'type': str},
            'Uninterruptible': {'type': bool, 'Options': [True, False]},
            'Helics logging level': {'type': int, 'Options': range(0, 10)},
        },
        "Logging": {
            'Logging Level': {'type': str, 'Options': ["DEBUG", "INFO", "WARNING" , "ERROR"]},
            'Log to external file': {'type': bool, 'Options': [True, False]},
            'Display on screen': {'type': bool, 'Options': [True, False]},
            'Clear old log file': {'type': bool, 'Options': [True, False]},
            'Log time step updates': {'type': bool, 'Options': [True, False]},
        },
        "MonteCarlo": {
            'Number of Monte Carlo scenarios': {'type': int},
        },
        "Plots": {
            'Create dynamic plots': {'type': bool, 'Options': [True, False]},
            'Open plots in browser': {'type': bool, 'Options': [True, False]},
        },
        "Project": {
            'Project Path': {'type': str},
            'Start time': {'type': str},
            'Simulation duration (min)': {'type': float},
            'Step resolution (sec)': {'type': float},
            'Loadshape start time': {'type': str},
            'Simulation range': {'type': dict},
            'Max Control Iterations' : {'type': int},
            'Convergence error percent threshold': {'type': float},
            'Skip export on convergence error': {'type': float},
            'Error tolerance': {'type': float},
            'Max error tolerance': {'type': float},
            'Simulation Type': {'type': str, 'Options': ["QSTS", "Dynamic", "Snapshot", "Monte Carlo"]},
            'Active Project': {'type': str},
            'Scenarios': {'type': list},
            'Active Scenario': {'type': str},
            'DSS File': {'type': str},
            'DSS File Absolute Path': {'type': bool, 'Options': [True, False]},
            'Return Results': {'type': bool, 'Options': [True, False]},
            'Control mode': {'type': str, 'Options': ["Static", "Time"]},
            'Disable PyDSS controllers': {'type': bool, 'Options': [True, False]},
            'Use Controller Registry': {'type': bool, 'Options': [True, False]},
        },
        "Profiles": {
            "Use profile manager":  {'type': bool, 'Options': [True, False]},
            "source_type": {'type': str},
            "source": {'type': str},
            "Profile mapping": {'type': str},
            "is_relative_path":  {'type': bool, 'Options': [True, False]},
            "settings": {'type': dict},
        },
        "Reports": {
            'Format': {'type': str, 'Options': ["csv", "h5"]},
            'Granularity': {'type': str, 'Options': [x.value for x in ReportGranularity]},
            'Types': {'type': list}
        },
    }


def validate_settings(dss_args):
    for category, params in dss_args.items():
        valid_settings = settings_dict[category]
        for key, ctype in params.items():
            assert (key in valid_settings), "category='{}' field='{}' is not a valid PyDSS argument".format(category,
                                                                                                            key)
            if valid_settings[key]['type'] == float and isinstance(ctype, int):
                ctype = float(ctype)
            assert (isinstance(ctype,
                               valid_settings[key]['type'])), "'{}' can only be a '{}' data type. Was passed {}".format(
                key, valid_settings[key]['type'], type(ctype)
            )
            if 'Options' in valid_settings[key]:
                if isinstance(valid_settings[key]['Options'], list):
                    assert (ctype in (valid_settings[key]['Options'])), \
                        "Invalid argument value '{}'. Possible values are: {}".format(ctype,
                                                                                      valid_settings[key]['Options'])
                elif isinstance(valid_settings[key]['Options'], range):
                    assert (min(valid_settings[key]['Options']) <= ctype <= max(valid_settings[key]['Options'])), \
                        "Value '{}' out of bounds for '{}'. Allowable range is: {}-{}".format(
                            ctype,
                            key,
                            min(valid_settings[key]['Options']),
                            max(valid_settings[key]['Options'])
                        )
            elif 'Enum' in valid_settings[key]:
                options = [x.value for x in valid_settings[key]['Enum']]
                assert ctype in options, "Invalid argument value '{}'. Possible values are {}".format(ctype, options)
                params[key] = valid_settings[key]['Enum'](ctype)

    for category, params in settings_dict.items():
        for key, ctype in params.items():
            assert (key in dss_args[
                category]), "category='{}' field='{}' definition is missing in the TOML file".format(category, key)

    try:
        Date = datetime.strptime(dss_args['Project']["Start time" ], DATE_FORMAT)
    except:
        raise Exception("For category='Project', field='Start time' should be a datetime string with format {}".format(
            DATE_FORMAT
        ))

    try:
        Date = datetime.strptime(dss_args['Project']["Loadshape start time"], DATE_FORMAT)
    except:
        raise Exception("For category='Project', field='Loadshape start time' should be a datetime string with format {}".format(
            DATE_FORMAT
        ))



    assert (dss_args['Frequency']['End frequency'] >= dss_args['Frequency']['Start frequency']), \
        "'End frequency' can not be smaller than 'Start frequency'"
    assert (os.path.exists(dss_args['Project']['Project Path'])), \
        "Project path {} does not exist.".format(dss_args['Project']['Project Path'])
    assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'], dss_args['Project']["Active Project"]))), \
        "Project '{}' does not exist.".format(dss_args['Project']["Active Project"])

    assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'],
                                        dss_args['Project']["Active Project"],
                                        'Scenarios',
                                        dss_args['Project']['Active Scenario']))), \
        "Scenario '{}' does not exist.".format(dss_args['Project']['Active Scenario'])
    assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'],
                                        dss_args['Project']["Active Project"],
                                        'DSSfiles',
                                        dss_args['Project']['DSS File']))), \
        "Master DSS file '{}' does not exist.".format(dss_args['Project']['DSS File'])

    for scenario in dss_args["Project"]["Scenarios"]:
        auto_snap_settings = scenario.get("snapshot_time_point_selection_config")
        if auto_snap_settings is None:
            scenario["snapshot_time_point_selection_config"] = {
                "mode": SnapshotTimePointSelectionMode.NONE,
                "start_time": "2020-1-1 00:00:00.0",
                "search_duration_min": 0.0,
            }
        else:
            auto_snap_settings["mode"] = SnapshotTimePointSelectionMode(auto_snap_settings["mode"])

    if "Reports" in dss_args:
        if [x for x in dss_args["Reports"]["Types"] if x["enabled"]]:
            if not dss_args["Exports"]["Log Results"]:
                raise InvalidConfiguration("Reports are only supported with Log Results")
    return


def dump_settings(settings, filename):
    """Dump the settings into a TOML file.

    Parameters
    ----------
    settings : dict
        A dict that may contain non-serializable instances like enums.

    Returns
    -------
    dict

    """
    with open(filename, "w") as f_out:
        toml.dump(settings, f_out, encoder=TomlEnumEncoder(settings.__class__))

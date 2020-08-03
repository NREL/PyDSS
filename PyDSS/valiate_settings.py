import os

settings_dict = {
        "Exports": {
            'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
            'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},
            # Feather is not supported because its underlying libraries do not support complex numbers
            'Export Format': {'type': str, 'Options': ["csv", "h5"]},
            'Export Compression': {'type': bool, 'Options': [True, False]},
            'Export Iteration Order': {'type': str, 'Options': ["ElementValuesPerProperty",
                                                                "ValuesByPropertyAcrossElements"]},
            'Export Elements': {'type': bool, 'Options': [True, False]},
            'Export Event Log': {'type': bool, 'Options': [True, False]},
            'Export Data Tables': {'type': bool, 'Options': [True, False]},
            'Export Data In Memory': {'type': bool, 'Options': [True, False]},
            'HDF Max Chunk Bytes': {'type': int, 'Options': range(16 * 1024, 1024 * 1024 + 1)},
            'Log Results': {'type': bool, 'Options': [True, False]},
            'Result Container': {'type': str, 'Options': ['ResultContainer', 'ResultData']},
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
            'Pre-configured logging': {'type': bool, 'Options': [True, False]},
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
            'Start Year': {'type': int, 'Options': range(1970, 2099)},
            'Start Day': {'type': int, 'Options': range(0, 365)},
            'Start Time (min)': {'type': float, 'Options': range(0, 1440)},
            'End Day': {'type': int, 'Options': range(0, 365)},
            'End Time (min)': {'type': float, 'Options': range(0, 1440)},
            'Date offset': {'type': int, 'Options': range(0, 365)},
            'Step resolution (sec)' : {'type': float},
            'Max Control Iterations' : {'type': int},
            'Error tolerance': {'type': float},
            'Simulation Type': {'type': str, 'Options': ["QSTS", "Dynamic", "Snapshot", "Monte Carlo"]},
            'Active Project': {'type': str},
            'Scenarios': {'type': list},
            'Active Scenario': {'type': str},
            'DSS File': {'type': str},
            'DSS File Absolute Path': {'type': bool, 'Options': [True, False]},
            'Return Results': {'type': bool, 'Options': [True, False]},
            'Control mode': {'type': str, 'Options': ["Static", "Time"]},
            'Disable PyDSS controllers': {'type': bool, 'Options': [True, False]},
        },
        "Profiles": {
            "Use profile manager":  {'type': bool, 'Options': [True, False]},
            "Profile store path": {'type': str},
            "Profile mapping": {'type': str},
        }
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

    for category, params in settings_dict.items():
        for key, ctype in params.items():
            assert (key in dss_args[
                category]), "category='{}' field='{}' definition is missing in the TOML file".format(category, key)

    assert (dss_args['Frequency']['End frequency'] >= dss_args['Frequency']['Start frequency']), \
        "'End frequency' can not be smaller than 'Start frequency'"
    assert (dss_args['Project']['End Day'] >= dss_args['Project']['Start Day']), \
        "'End day' can not be smaller than 'Start day'"
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
    return
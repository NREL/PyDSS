from PyDSS.pyAnalyzer.dssSimulationResult import ResultObject
from PyDSS.pyAnalyzer.dssGraphicsGenerator import CreatePlots
from PyDSS import dssInstance
import subprocess
import click
import toml
import sys
import os

toml_file_path = r'C:\Users\alatif\Desktop\PyDSS-Projects\MySpohnTest\PyDSS Scenarios\self_consumption\PyDSS_settings.toml'

valid_settings = {
        'Log Results' : {'type': bool, 'Options': [True, False]},
        'Return Results': {'type': bool, 'Options': [True, False]},
        'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
        'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},

        'Create dynamic plots': {'type': bool, 'Options': [True, False]},
        'Open plots in browser': {'type': bool, 'Options': [True, False]},

        'Project Path': {'type': str},
        'Start Year' : {'type': int, 'Options': range(1970, 2099)},
        'Start Day' : {'type': int, 'Options': range(0, 365)},
        'Start Time (min)' : {'type': float, 'Options': range(0, 1440)},
        'End Day' : {'type': int, 'Options': range(0, 365)},
        'End Time (min)' : {'type': float, 'Options': range(0, 1440)},
        'Date offset' : {'type': int, 'Options': range(0, 365)},
        'Step resolution (sec)' : {'type': float},
        'Max Control Iterations' : {'type': int},
        'Error tolerance' : {'type': float},
        'Simulation Type' : {'type': str, 'Options': ["QSTS", "Dynamic", "Snapshot", "Monte Carlo"]},
        'Active Project' : {'type': str},
        'Active Scenario' : {'type': str},
        'DSS File' : {'type': str},

        'Logging Level' : {'type': str, 'Options': ["DEBUG", "INFO", "WARNING" , "ERROR"]},
        'Log to external file'  : {'type': bool, 'Options': [True, False]},
        'Display on screen' : {'type': bool, 'Options': [True, False]},
        'Clear old log file' : {'type': bool, 'Options': [True, False]},

        'Control mode' : {'type': str, 'Options': ["Static", "Time"]},
        'Disable PyDSS controllers' : {'type': bool, 'Options': [True, False]},

        'Enable frequency sweep' : {'type': bool, 'Options': [True, False]},
        'Fundamental frequency' : {'type': int, 'Options': [50, 60]},
        'Start frequency' : {'type': float},
        'End frequency' : {'type': float},
        'frequency increment' : {'type': float},
        'Neglect shunt admittance' : {'type': bool, 'Options': [True, False]},
        'Percentage load in series' : {'type': float, 'Options': range(0, 100)},

        'Number of Monte Carlo scenarios' : {'type': int},
}

def RunSimulations(Batch_TOML_file):
    settings_text = ''
    f = open(Batch_TOML_file, "r")
    text = settings_text.join(f.readlines())
    Simulations_args = toml.loads(text)
    f.close()
    SimulationResults = {}

    if Simulations_args['Simulations']['Run_bokeh_server']:
        BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)


    for scenario in Simulations_args['Simulations']['Scenarios']:
        dss_args, ResultObject = RunScenario(
            scenario,
            Simulations_args['Simulations']['Run_simulations'],
            Simulations_args['Simulations']['Generate_visuals']
        )
        SimulationResults['{}-{}-{}-{}-{}'.format(
            dss_args["Active Project"],
            dss_args["Active Scenario"],
            dss_args["Start Year"],
            dss_args["Start Day"],
            dss_args["End Day"],
        )] = (dss_args, ResultObject)

    if Simulations_args['Simulations']['Generate_visuals']:
        CreatePlots(Simulations_args, SimulationResults)

    if Simulations_args['Simulations']['Run_bokeh_server']:
        BokehServer.terminate()
    return


def RunScenario(Scenario_TOML_file_path, run_simulation=True, generate_visuals=False):
    settings_text = ''
    f = open(Scenario_TOML_file_path, "r")
    text = settings_text.join(f.readlines())
    dss_args = toml.loads(text, _dict=dict)
    __validate_settings(dss_args)
    f.close()

    print(run_simulation)
    if run_simulation:
        dss = dssInstance.OpenDSS(**dss_args)
        print('Running scenario: {}'.format(Scenario_TOML_file_path))
        if dss_args['Simulation Type'] == "Monte Carlo":
            #TODO: Fix the broken MC code
            dss.RunMCsimulation(MCscenarios=dss_args['Number of Monte Carlo scenarios'])
        else:
            dss.RunSimulation()
        dss.DeleteInstance()
        del dss
    # dss.CreateGraph(Visualize=True)

    if generate_visuals:
        return dss_args, ResultObject(os.path.join(
            dss_args['Project Path'],
            dss_args["Active Project"],
            'Exports',
            dss_args['Active Scenario']
        ))
    else:
        return dss_args, None

def __validate_settings(dss_args):
    for key, ctype in dss_args.items():
        assert (key in valid_settings), "'{}' is not a valid PyDSS argument".format(key)
        assert (isinstance(ctype, valid_settings[key]['type'])), "'{}' can only be a '{}' data type. Was passed {}".format(
            key, valid_settings[key]['type'], type(ctype)
        )
        if 'Options' in valid_settings[key]:
            if isinstance(valid_settings[key]['Options'], list):
                assert (ctype in  (valid_settings[key]['Options'])),\
                    "Invalid argument value '{}'. Possible values are: {}".format(ctype ,valid_settings[key]['Options'])
            elif isinstance(valid_settings[key]['Options'], range):
                assert (min(valid_settings[key]['Options']) <= ctype <= max(valid_settings[key]['Options'])), \
                    "Value '{}' out of bounds for '{}'. Allowable range is: {}-{}".format(
                        ctype,
                        key,
                        min(valid_settings[key]['Options']),
                        max(valid_settings[key]['Options'])
                    )

    for key, ctype in valid_settings.items():
        assert (key in dss_args), "'{}' definition is missing in the TOML file".format(key)

    assert (dss_args['End frequency'] >= dss_args['Start frequency']),\
        "'End frequency' can not be smaller than 'Start frequency'"
    assert (dss_args['End Day'] >= dss_args['Start Day']), \
        "'End day' can not be smaller than 'Start day'"
    assert (os.path.exists(dss_args['Project Path'])), \
        "Project path {} does not exist.".format(dss_args['Project Path'])
    assert (os.path.exists(os.path.join(dss_args['Project Path'], dss_args["Active Project"]))), \
        "Project '{}' does not exist.".format(dss_args["Active Project"])

    assert (os.path.exists(os.path.join(dss_args['Project Path'],
                                        dss_args["Active Project"],
                                        'PyDSS Scenarios',
                                        dss_args['Active Scenario']))), \
        "Scenario '{}' does not exist.".format( dss_args['Active Scenario'])

    assert (os.path.exists(os.path.join(dss_args['Project Path'],
                                        dss_args["Active Project"],
                                        'DSSfiles',
                                        dss_args['DSS File']))), \
        "Master DSS file '{}' does not exist.".format(dss_args['DSS File'])
    return

if __name__ == '__main__':
    Batch_file = r'C:\Users\alatif\Desktop\PyDSS-Projects\Harmonics_Snapshot\PyDSS Scenarios\BatchRunSettings.toml'
    RunSimulations(Batch_file)
    #RunSimulation(Batch_file)
    print('End')
    # process(sys.argv[3:])


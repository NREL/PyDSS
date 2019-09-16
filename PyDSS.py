from PyDSS import dssInstance
from PyDSS import dssVisualizer
import subprocess
import logging
import click
import toml
import os

toml_file_path = r'C:\Users\alatif\Desktop\PyDSS-Projects\Test_pydss_project\PyDSS_settings.toml'

valid_settings = {
        'Log Results' : bool,
        'Return Results': bool,
        'Export Mode': str,
        'Export Style': str,

        'Create dynamic plots' : bool,
        'Open plots in browser' : bool,

        'Project Path': str,
        'Start Year' : int,
        'Start Day' : int,
        'Start Time (min)' : float,
        'End Day' : int,
        'End Time (min)' : float,
        'Date offset' : int,
        'Step resolution (sec)' : float,
        'Max Control Iterations' : int,
        'Error tolerance' : float,
        'Simulation Type' : str,
        'Active Project' : str,
        'Active Scenario' : str,
        'DSS File' : str,

        'Logging Level' : str,
        'Log to external file'  : bool,
        'Display on screen' : bool,
        'Clear old log file' : bool,

        'Control mode' : str,
        'Disable PyDSS controllers' : bool,

        'Enable frequency sweep' : bool,
        'Fundamental frequency' : float,
        'Start frequency' : float,
        'End frequency' : float,
        'frequency increment' : float,
        'Neglect shunt admittance' : bool,
        'Percentage load in series' : float,
}

@click.command()
# Settings for exporting results
@click.option('--toml_path', default=toml_file_path, type=click.STRING, help='Path for the toml pile')


def RunSimulation(**kwargs):
    TOML_path = kwargs.get('toml_path')
    settings_text = ''
    f = open(TOML_path, "r")
    text = settings_text.join(f.readlines())
    dss_args = toml.loads(text, _dict=dict)
    validate_settings(dss_args)
    f.close()


    #BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
    dss = dssInstance.OpenDSS(**dss_args)
    # visualizer = dssVisualizer.VisualizerInstance(**dss_args)
    #dss.CreateGraph(Visualize=True)
    dss.RunSimulation()
    # BokehServer.terminate()
    # DSS.RunMCsimulation(MCscenarios = 3)
    dss.DeleteInstance()
    # os.system('pause')
    # del dss

def validate_settings(dss_args):
    for key, ctype in dss_args.items():
        assert (key in valid_settings), "'{}' is not a valid PyDSS argument".format(key)
        assert (isinstance(ctype, valid_settings[key])), "'{}' can only be a '{}' data type. Was passed {}".format(
            key, valid_settings[key], type(ctype)
        )
    return


if __name__ == '__main__':
    RunSimulation()
    print('End')
    # process(sys.argv[3:])


from multiprocessing import Pool
from PyDSS import dssInstance
import subprocess
import logging
import os


def pyDSSinstance(kwargs):
    dssArgs = {
        # Settings for exporting results
        'Log Results': True,
        'Return Results': False,
        'Export Mode': 'byClass',  # 'byClass'        , 'byElement'
        'Export Style': 'Single file',  # 'Separate files' , 'Single file'

        # Plot Settings
        'Network layout': False,
        'Time series': False,
        'XY plot': False,
        'Sag plot': False,
        'Histogram': False,
        'GIS overlay': False,

        # Simulation Settings
        'Start Day': 156,  # 156, 286
        'End Day': 163,  # 163, 293
        'Step resolution (min)': 15,
        'Max Control Iterations': 10,
        'Simulation Type': 'Daily',
        'Active Project': None,
        'Active Scenario': None,
        'DSS File': 'MasterCircuit.dss',
        'Error tolerance': 0.005,

        # Logger settings
        'Logging Level': logging.DEBUG,
        'Log to external file': True,
        'Display on screen': True,
        'Clear old log file': False,
    }

    dssArgs.update(kwargs)
    DSS = dssInstance.OpenDSS(**dssArgs)
    DSS.RunSimulation()
    DSS.DeleteInstance()
    return


def RunBokehServer():
    p = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
    return


if __name__ == '__main__':
    project = 'Spohn-Curtailment'
    folder = '/Users/mblonsky/Documents/GitHub/PyDSS/Inputs/{}/Scenarios'.format(project)
    scenarios = [d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d))]
    print(scenarios)


    def master_file(s):
        tap_changes = {
            '1': '',
            '0975': '_0975',
            '095': '_095'
        }
        # return 'MasterCircuit{}.dss'.format(scenario_to_master[s.split('-')[-1]])
        return 'MasterCircuit_{}min.dss'.format(str(step_res(s)))


    def step_res(s):
        return 15 if '1min' not in s else 1


    kwargs = [{'Active Project': project,
               'Active Scenario': s,
               'DSS File': master_file(s),
               'Step resolution (min)': step_res(s)} for s in scenarios]
    RunBokehServer()

    pool = Pool(processes=4)
    pool.map(pyDSSinstance, kwargs)

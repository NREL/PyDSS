from multiprocessing import Pool
import dssInstance
import subprocess
import logging
import os

def pyDSSinstance(Scenario):
    # Settings for exporting results
    RO = {
        'Log Results'    : True,
        'Export Mode'    : 'byClass',             # 'byClass'        , 'byElement'
        'Export Style'   : 'Single file',         # 'Seperate files' , 'Single file'
    }
    # Plot Settings
    PO = {
        'Network layout' : False,
        'Time series'    : False,
        'XY plot'        : False,
        'Sag plot'       : False,
        'Histogram'      : False,
        'GIS overlay'    : False,
    }
    # Simulation Settings
    SS = {
        'Start Day'              : 157,
        'End Day'                : 164,
        'Step resolution (min)'  : 15,
        'Max Control Iterations' : 10,
        'Error tolerance'        : 1,
        'Simulation Type'        : 'Daily',
        'Active Project'         : 'HECO',
        'Active Scenario'        : Scenario,
        'DSS File'               : 'MasterCircuit_Mikilua_baseline2.dss',   #'MasterCircuit_Mikilua_keep.dss'
    }
    # Logger settings
    LO =  {
        'Logging Level'          : logging.DEBUG,
        'Log to external file'   : True,
        'Display on screen'      : False,
        'Clear old log files'    : False,
    }

    DSS = dssInstance.OpenDSS(PlotOptions = PO , ResultOptions=RO, SimulationSettings=SS, LoggerOptions=LO)
    DSS.RunSimulation()

    os.system('pause')
    DSS.DeleteInstance()
    return

def RunBokehServer():
    p = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
    return

if __name__ == '__main__':
    Scenarios = ['HP-Legacy', 'HP-VW']
    RunBokehServer()
    pool = Pool(processes=len(Scenarios))
    pool.map(pyDSSinstance, Scenarios)


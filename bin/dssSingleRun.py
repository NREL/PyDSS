#from PyQt5.uic.Compiler.qtproxies import i18n_string
import PyDSS.dssInstance as dssInstance
import subprocess
import logging
#import os

dssArgs = {
    # Settings for exporting results
    'Log Results'    : True,
    'Return Results' : True,
    'Export Mode'    : 'byClass',           # 'byClass'        , 'byElement'
    'Export Style'   : 'Single file',         # 'Separate files' , 'Single file'

    # Plot Settings
    'Network layout' : False,
    'Time series'    : False,
    'XY plot'        : False,
    'Sag plot'       : False,
    'Histogram'      : False,
    'GIS overlay'    : False,

    # Simulation Settings
    'Start Day'              : 243, # 156, maybe 286
    'End Day'                : 244, # 163, maybe 293
    'Step resolution (min)'  : 15,
    'Max Control Iterations' : 10,
    'Simulation Type'        : 'Daily',
    'Active Project'         : 'Mikilua',
    'Active Scenario'        : 'CSS30VV-VV-D',
    'DSS File'               : 'MasterCircuit_Mikilua_baseline2_CSS30.dss',
    'Error tolerance'        : 1,

    # Logger settings
    'Logging Level'          : logging.DEBUG,
    'Log to external file'   : True,
    'Display on screen'      : True,
    'Clear old log files'    : False,
}

BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
DSS = dssInstance.OpenDSS(**dssArgs)
DSS.RunSimulation()
BokehServer.terminate()
DSS.DeleteInstance()
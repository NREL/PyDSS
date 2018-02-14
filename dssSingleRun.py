from PyQt5.uic.Compiler.qtproxies import i18n_string

import dssInstance
import subprocess
import logging
import os

# Settings for exporting results
RO = {
    'Log Results'    : True,
    'Export Mode'    : 'byClass',           # 'byClass'        , 'byElement'
    'Export Style'   : 'Single file',         # 'Seperate files' , 'Single file'
}
# Plot Settings
PO = {
    'Network layout' : False,
    'Time series'    : True,
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
    'Simulation Type'        : 'Daily',
    'Active Project'         : 'HECO',
    'Active Scenario'        : 'HP-VV-VW-R',
    'DSS File'               : 'MasterCircuit_Mikilua_baseline2.dss',   #'MasterCircuit_Mikilua_keep.dss'
}
# Logger settings
LO =  {
    'Logging Level'          : logging.DEBUG,
    'Log to external file'   : True,
    'Display on screen'      : True,
    'Clear old log files'    : True,
}

p = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
DSS = dssInstance.OpenDSS(PlotOptions = PO , ResultOptions=RO, SimulationSettings=SS, LoggerOptions=LO)
DSS.RunSimulation()
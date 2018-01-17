
import dssInstance
import warnings
import os
warnings.filterwarnings('ignore')
# Settings for exporting results
RO = {
    'Log Results'    : True,
    'Export Mode'    : 'byElement',           # 'byClass'        , 'byElement'
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
    'Start Day'              : 4,
    'End Day'                : 5,
    'Step resolution (min)'  : 15,
    'Max Control Iterations' : 10,
    'Simulation Type'        : 'Daily',
    'Active Project'         : 'HECO',
    'Active Scenario'        : 'HP-VV',
    'DSS File'               : 'MasterCircuit_Mikilua_baseline3.dss',
}

# DssFile =  {
#     0 : 'MasterCircuit_Mikilua_keep.dss',
#     1 : 'MasterCircuit_Mikilua_baseline3.dss',
# }

DSS = dssInstance.OpenDSS(PlotOptions = PO , ResultOptions=RO, SimulationSettings=SS)
DSS.RunSimulation()

os.system('pause')
DSS.DeleteInstance()
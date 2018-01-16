
import dssInstance
import warnings
import os
warnings.filterwarnings('ignore')

RO = {
    'Log Results'    : None,
    'Export Mode'    : 'byElement',           # 'byClass'        , 'byElement'
    'Export Style'   : 'Single file',         # 'Seperate files' , 'Single file'
}

PO = {
    'Network layout' : False,
    'Time series'    : True,
    'XY plot'        : False,
    'Sag plot'       : False,
    'Histogram'      : False,
    'GIS overlay'    : False,
}

SS = {
    'Simulation Type'        : 'Daily',
    'Start Day'              : 4,
    'End Day'                : 5,
    'Step resolution (min)'  : 15,
    'Max Control Iterations' : 10,
}

DssFile =  {
    0 : 'MasterCircuit_Mikilua_keep.dss',
    1 : 'MasterCircuit_Mikilua_baseline3.dss',
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotOptions = PO , ResultOptions=RO, SimulationSettings=SS,
                          dssMainFile = DssFile[1])

DSS.RunSimulation()

os.system('pause')
DSS.DeleteInstance()
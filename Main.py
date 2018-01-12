
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
    'SimType'        : 'Daily',
    'StartTime'      : 0,
    'Time Steps'     : 96,
    'Min/Time step'  : 15,
    'MaxCtrlItrs'    : 20,
}

DssFile =  {
    0 : 'MasterCircuit_Mikilua_keep.dss',
    1 : 'MasterCircuit_Mikilua_baseline3.dss',
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotOptions = PO , ResultOptions=RO,
                          dssMainFile = DssFile[1])

# DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotOptions = PO , ResultOptions=RO,
#                           dssMainFile = 'MasterCircuit_Mikilua_keep.dss')

DSS.RunSimulation(Steps = 96*5, ControllerMaxItrs = 10) #8760

os.system('pause')
DSS.DeleteInstance()
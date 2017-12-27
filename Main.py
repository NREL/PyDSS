
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
    'Time series'    : False,
    'XY plot'        : False,
    'Sag plot'       : False,
    'Histogram'      : True,
}

SS = {
    'SimType'        : 'Daily',
    'StartTime'      : 0,
    'Time Steps'     : 96,
    'Min/Time step'  : 15,
    'MaxCtrlItrs'    : 20,
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotOptions = PO , ResultOptions=RO,
                          dssMainFile = 'MasterCircuit_Mikilua_keep.dss')
DSS.RunSimulation(Steps = 96*3, ControllerMaxItrs = 20) #8760

os.system('pause')
DSS.DeleteInstance()
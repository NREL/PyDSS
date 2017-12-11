
import dssInstance
import warnings
warnings.filterwarnings('ignore')

RO = {
    'Log Results'    : False,
    'Export Mode'    : 'byClass',           # 'byClass'        , 'byElement'
    'Export Style'   : 'Single file',    # 'Seperate files' , 'Single file'
}

PO = {
    'Network layout' : False,
    'Time series'    : False,
    'XY plot'        : False,
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
DSS.RunSimulation(Steps = 96, ControllerMaxItrs = 20) #8760
DSS.DeleteInstance()

import dssInstance
import warnings
warnings.filterwarnings('ignore')

EL = {
    #'Loads':['Powers']
}

PO = {
    'Network layout' : True,
    'Time series' : False,
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotOptions = PO , ExportList=EL,
                          dssMainFile = 'MasterCircuit_Mikilua_keep.dss')
DSS.RunSimulation(Steps = 96, ControllerMaxItrs = 20) #8760
DSS.DeleteInstance()
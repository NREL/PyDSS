import dssInstance
import socket
import struct
import sys


EL = {
    'Loads':['Powers']
#
}


PL = {
    'Network layout': { 'FileName': 'Network layout.html',
                        'Path'    : None,
                        'Width'   : 1400,
                        'Height'  : 850
                        },

    # 'Time series': {'FileName': 'Time Series.html',
    #                 'Path': None,
    #                 'X' : None,
    #                 'Y' : None,
    #                 'Width': 1200,
    #                 'Height': 600
    #                 },
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotList = PL , ExportList=EL)
DSS.RunSimulation(Steps = 96, ControllerMaxItrs = 20) #8760
DSS.DeleteInstance()
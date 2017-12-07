import dssInstance
import socket
import struct
import sys


EL = {
    'Loads':['Powers']
}

PL = {
    # 'Network layout': { 'FileName': 'Network layout.html',
    #                     'Path'    : None,
    #                     'Width'   : 1400,
    #                     'Height'  : 850
    #                     },

    'Time series.1':   {'FileName'     : 'Time Series.html',
                        'yObjectType'  : 'Element',
                        'yObjName'     : 'Storage.storagebus',
                        'yScaler'      : [1 , -1, -1, 1],
                        'Properties'   : ['p.%stored','v.Powers', 'v.Powers', 'v.VoltagesMagAng'],
                        'index'        : [None , 'SumEven', 'SumOdd', 'Index=1', ],
                        'Width'        : 1400,
                        'Height'       : 350,
                        },

    'Time series.2':   {'FileName'     : 'Time Series.html',
                        'yObjectType'  : 'Bus',
                        'yObjName'     : 'storagebus',
                        'yScaler'      : [1],
                        'Properties'   : ['v.puVmagAngle'],
                        'index'        : ['Even'],
                        'Width'        : 1400,
                        'Height'       : 350,
                        },

    'Time series.3':   {'FileName'     : 'Time Series.html',
                        'yObjectType'  : 'Circuit',
                        'yObjName'     : '',
                        'yScaler'      : [-1],
                        'Properties'   : ['v.TotalPower'],
                        'index'        : ['SumEven'],
                        'Width'        : 1400,
                        'Height'       : 350,
                        },
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', PlotList = PL , ExportList=EL, dssMainFile = 'MasterCircuit_Mikilua_keep.dss')
DSS.RunSimulation(Steps = 96, ControllerMaxItrs = 20) #8760
DSS.DeleteInstance()
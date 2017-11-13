import dssInstance
import socket
import struct
import sys
# EL = {
#     'Loads':['Voltages','Enabled'],
#     'Lines':['CurrentsMagAng']
# }

CL = {
    'PV Controller'     : {'PVSystem.645.2' :  {'Measured Element'  : 'Line.650632',
                                                'Measured Variable' : 'Powers',
                                                'Qcontrol'          : 'None', # CPF, VPF, VV, Legacy
                                                'Pcontrol'          : 'None', #None, VW
                                                'Priority'          : 'Equal', # Equal, Var, Watt
                                                'DampCoef'          : 0.9,
                                                'pfMax'             : 1,
                                                'pfMin'             : 0.95,
                                                'uMax'              : 1.05,
                                                'uMin'              : 0.95,
                                                'uDbMax'            : 1.00,
                                                'uDbMin'            : 1.00,
                                                'QlimPU'            : 0.4,
                                                'PFlim'             : 0.85,}},

    'Storage Controller': {'Storage.671'    :  {'Meas from Circuit' : True,
                                                'Measured Element'  : 'Line.650632',
                                                'Measured Variable' : 'Powers',
                                                'Qcontrol'          : 'Constant Power Factor', #'Variable Power Factor','None', 'Volt Var Control'
                                                'Pcontrol'          : 'Peak Shaving', #, 'None',#'Real Time', 'Time Triggered','Scheduled','Peak Shaving','Capacity Firming'
                                                'PS_ub'             : 3000,
                                                'PS_lb'             : 1100,
                                                'DampCoef'          : 0.5,
                                                'CF_dP_ub'          : 50,
                                                'CF_dP_lb'          : -50,
                                                'HrCharge'          : 2,
                                                'HrDischarge'       : 15,
                                                '%rateCharge'       : 100,
                                                '%rateDischarge'    : 100,
                                                '%kWOut'            : 50,
                                                'pf'                : 0.95,
                                                'pfMax'             : 1,
                                                'pfMin'             : 0.95,
                                                'uMax'              : 1.05,
                                                'uMin'              : 0.95,
                                                'uDbMax'            : 1.00,
                                                'uDbMin'            : 1.00,
                                                'QlimPU'            : 0.4,
                                                'PFlim'             : 0.85,
                                                'Days'              : 1,
                                                'Schedule'          : [0, 0, -1, 0, 1, 0, 0]}},
    }

PL = {
    'Network layout': { 'FileName': 'Network layout.html',
                        'Path'    : None,
                        'Width'   : 900,
                        'Height'  : 600
                        },

    # 'Time series': {'FileName': 'Time Series.html',
    #                 'Path': None,
    #                 'X' : None,
    #                 'Y' : None,
    #                 'Width': 1200,
    #                 'Height': 600
    #                 },
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', ControllerList = CL, PlotList = PL )
DSS.RunSimulation(Steps = 1440, ControllerMaxItrs = 20) #8760
DSS.DeleteInstance()
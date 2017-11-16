import dssInstance
import socket
import struct
import sys
# EL = {
#     'Loads':['Voltages','Enabled'],
#     'Lines':['CurrentsMagAng']
# }

CL = {
    'PV Controller'     : {'PVSystem.675_1' :  {'Qcontrol'          : 'VVar',  # CPF, VPF, VVar, None
                                                'Pcontrol'          : 'None',    # None, VW
                                                'HasConnLoad'       : True,
                                                'DampCoef'          : 1.00,
                                                'pf'                : 0.85,
                                                'Pmin'              : 0.15,
                                                'Pmax'              : 0.85,
                                                'pfMax'             : 0.8,
                                                'pfMin'             : -0.8,
                                                'uMinC'             : 1.00,
                                                'uMaxC'             : 1.07,
                                                'uMax'              : 1.05,
                                                'uMin'              : 0.95,
                                                'uDbMax'            : 1.00,
                                                'uDbMin'            : 1.00,
                                                'QlimPU'            : 0.4,
                                                'PFlim'             : 0.8,
                                                'Ambient Temp'      : 30,
                                                'Efficiency'        : 100,
                                                '%Cutin'            : 0,
                                                '%Cutout'           : 0,
                                                'Irradiance'        : 1}},

    # 'Storage Controller': {'Storage.671'    :  {'Meas from Circuit' : True,
    #                                             'Measured Element'  : 'Line.650632',
    #                                             'Measured Variable' : 'Powers',
    #                                             'Qcontrol'          : 'None', #'Variable Power Factor','None', 'Volt Var Control'
    #                                             'Pcontrol'          : 'None', #, 'None',#'Real Time', 'Time Triggered','Scheduled','Peak Shaving','Capacity Firming'
    #                                             'PS_ub'             : 3000,
    #                                             'PS_lb'             : 1100,
    #                                             'DampCoef'          : 0.5,
    #                                             'CF_dP_ub'          : 50,
    #                                             'CF_dP_lb'          : -50,
    #                                             'HrCharge'          : 2,
    #                                             'HrDischarge'       : 15,
    #                                             '%rateCharge'       : 100,
    #                                             '%rateDischarge'    : 100,
    #                                             '%kWOut'            : 50,
    #                                             'pf'                : 0.95,
    #                                             'pfMax'             : 1,
    #                                             'pfMin'             : 0.95,
    #                                             'uMax'              : 1.05,
    #                                             'uMin'              : 0.95,
    #                                             'uDbMax'            : 1.00,
    #                                             'uDbMin'            : 1.00,
    #                                             'QlimPU'            : 0.4,
    #                                             'PFlim'             : 0.85,
    #                                             'Days'              : 1,
    #                                             'Schedule'          : [0, 0, -1, 0, 1, 0, 0]}},
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
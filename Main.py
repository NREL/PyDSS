import dssInstance
import socket
import struct
import sys
# EL = {
#     'Loads':['Voltages','Enabled'],
#     'Lines':['CurrentsMagAng']
# }

CL = {
    'Storage Controller': {'Storage.671' : {'Meas from Circuit' : True,
                                            'Measured Element'  : 'Line.650632',
                                            'Measured Variable' : 'Powers',
                                            'Qcontrol'          : 'None', #'Variable Power Factor','None', 'Volt Var Control'
                                            'Pcontrol'          : 'Real Time', #, 'None',#'Peak Shaving', 'Time Triggered','Scheduled'
                                            'PS_ub'             : 1700,
                                            'PS_lb'             : 1500,
                                            'HrCharge'          : 2,
                                            '%rateCharge'       : 100,
                                            '%rateDischarge'    : 100,
                                            '%kWOut'            : 50,
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
    # 'Network layout': { 'FileName': 'Network layout.html',
    #                     'Path'    : None,
    #                     'Width'   : 900,
    #                     'Height'  : 600
    #                     },

    'Time series': {'FileName': 'Time Series.html',
                    'Path': None,
                    'X' : None,
                    'Y' : None,
                    'Width': 1200,
                    'Height': 600
                    },
}

DSS = dssInstance.OpenDSS(SimType = 'Daily', ControllerList = CL, PlotList = PL )
#DSS.RunSimulation(1440) #8760
port = 5000

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', port)
sock.bind(server_address)
sock.listen(1)
while True:
    print ('waiting for a connection')
    connection, client_address = sock.accept()
    while True:
        try:
            print ('connection from', client_address)

            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(1024)

                if data:
                    numDoubles = int(len(data) / 8)
                    tag = str(numDoubles)+'d'
                    Data = list(struct.unpack(tag, data))
                    print ('Recieved --> ', Data)
                    CurrTime = Data[0]
                    initSOC = Data[1]
                    BatteryOut = Data[2]
                    Results = DSS.CalcState(CurrTime, initSOC, BatteryOut)
                    Results = [float(i) for i in Results]
                    # print (Results)
                    connection.sendall(struct.pack('%sd' % len(Results), *Results))
        finally:
            # Clean up the connection
            connection.close()

DSS.DeleteInstance()
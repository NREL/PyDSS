import socket
import struct

class SocketController:
    def __init__(self, ElmObject, Settings, dssInstance, ElmObjectList,dssSolver):
        self.__ControlledElm = ElmObject
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name

        self.IP = Settings['IP']
        self.Port = Settings['Port']
        self.Encoding = Settings['Encoding']
        self.BufferSize = Settings['Buffer']
        self.Index = Settings['Index'].split(',') if ',' in Settings['Index'] else [Settings['Index']]
        self.Inputs  = Settings['Inputs'].split(',') if ',' in Settings['Inputs'] else [Settings['Inputs']]
        self.Outputs = Settings['Outputs'].split(',') if ',' in Settings['Outputs'] else [Settings['Outputs']]
        self.Socket = self.__CreateClient()
        return

    def __CreateClient(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a socket object
        s.connect((self.IP, self.Port))
        return s

    def Update_Q(self, Time, UpdateResults):
        Values = []
        for Variable in self.Inputs:
            Val =  self.__ControlledElm.GetValue(Variable)
            if isinstance(Val, list):
                Values.extend(Val)
            else:
                Values.extend([Val])
        self.Socket.sendall(struct.pack('%sd' % len(Values), *Values))

        Data = self.Socket.recv(self.BufferSize)
        if Data:
            numDoubles = int(len(Data) / 8)
            tag = str(numDoubles) + 'd'
            Data = list(struct.unpack(tag, Data))
            print('Recieved --> ', Data)

            for i, Variable in enumerate(self.Outputs):
                self.__ControlledElm.SetParameter(Variable, Data[0])
        return 0

    def Update_P(self, Time, UpdateResults):
        return 0
from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract
import socket
import struct

class SocketController(ControllerAbstract):
    """Allows pydss object to inteface with external software using socket communication. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

            :param ElmObject: A :class:`pydss.dssElement.dssElement` object that wraps around any OpenDSS element
            :type FaultObj: class:`pydss.dssElement.dssElement`
            :param Settings: A dictionary that defines the settings for the PvController.
            :type Settings: dict
            :param dssInstance: An :class:`opendssdirect` instance
            :type dssInstance: :class:`opendssdirect`
            :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
            :type ElmObjectList: dict
            :param dssSolver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
            :type dssSolver: :mod:`pydss.SolveMode`
            :raises: socket.error if the connection fails

    """

    def __init__(self, ElmObject, Settings, dssInstance, ElmObjectList,dssSolver):
        super(SocketController, self).__init__(ElmObject, Settings, dssInstance, ElmObjectList, dssSolver)
        self.Time = -1
        self.__ControlledElm = ElmObject
        self.Class, self.Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + self.Class + '_' + self.Name
        #assert (Class.lower() == 'regulator'), 'PvControllerGen works only with an OpenDSS Regulator element'
        self.IP = Settings['IP']
        self.Port = Settings['Port']
        self.Encoding = Settings['Encoding']
        self.BufferSize = Settings['Buffer']
        self.Index = Settings['Index'].split(',') if ',' in Settings['Index'] else [Settings['Index']]
        self.Inputs = Settings['Inputs'].split(',') if ',' in Settings['Inputs'] else [Settings['Inputs']]
        self.Outputs = Settings['Outputs'].split(',') if ',' in Settings['Outputs'] else [Settings['Outputs']]
        self.Socket = self.__CreateClient()
        return

    def __CreateClient(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a socket object
        s.connect((self.IP, self.Port))
        return s

    def Update(self, Priority, Time, UpdateResults):

        # self.TimeChange = self.Time != (Priority, Time)
        # self.Time = (Priority, Time)
        self.TimeChange = self.Time != Time
        self.Time = Time

        if self.TimeChange and Priority==0:
            Values = []
            for Variable in self.Inputs:
                Val =  self.__ControlledElm.GetValue(Variable)
                if isinstance(Val, list):
                    Values.extend(Val)
                else:
                    Values.extend([Val])
            self.Socket.sendall(struct.pack('%sd' % len(Values), *Values))
        if self.TimeChange and Priority == 1:
            Data = self.Socket.recv(self.BufferSize)
            if Data:
                numDoubles = int(len(Data) / 8)
                tag = str(numDoubles) + 'd'
                Data = list(struct.unpack(tag, Data))
                for i, Variable in enumerate(self.Outputs):
                    self.__ControlledElm.SetParameter(Variable, Data[0])
        return 0

    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.Class, self.Name)

    def debugInfo(self):
        pass

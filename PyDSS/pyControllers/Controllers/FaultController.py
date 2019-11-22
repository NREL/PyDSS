from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract

class FaultController(ControllerAbstract):
    """The class is used to induce faults on bus for dynamic simulation studies. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class. 

    :param FaultObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type FaultObj: class:`PyDSS.dssElement.dssElement`
    :param Settings: A dictionary that defines the settings for the faul controller.
    :type Settings: dict
    :param dssInstance: An :class:`opendssdirect` instance
    :type dssInstance: :class:`opendssdirect` instance
    :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit ojects
    :type ElmObjectList: dict
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`
    :raises: AssertionError  if 'FaultObj' is not a wrapped OpenDSS Fault element

    """
    def __init__(self, FaultObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Constructor method
        """

        super(FaultController).__init__()    
        self.P_old = 0
        self.Time = -1
        self.__Locked = False
        self.__dssSolver = dssSolver
        self.__FaultObj = FaultObj
        self.__Settings = Settings
        FaultObj.SetParameter('bus1', Settings['Bus1'])
        FaultObj.SetParameter('bus2', Settings['Bus2'])
        FaultObj.SetParameter('r', Settings['Fault resistance'])
        print(FaultObj, Settings)
        Class, Name = self.__FaultObj.GetInfo()
        assert (Class.lower() == 'fault'), 'FaultController works only with an OpenDSS Fault element'
        self.__Name = 'pyCont_' + Class + '_' + Name
        self.__init_time = dssSolver.GetDateTime()
        self.__Settings['Fault end time (sec)'] = self.__Settings['Fault start time (sec)'] + \
                                                  self.__Settings['Fault duration (sec)']
        return

    def Update(self, Priority, Time, UpdateResults):
        """Induces and removes a fault as the simulation runs as per user defined settings. 
        """
        time = (self.__dssSolver.GetDateTime() - self.__init_time).total_seconds()

        if time >= self.__Settings['Fault start time (sec)'] and time < self.__Settings['Fault end time (sec)']:
            self.__FaultObj.SetParameter('enabled', 'yes')
        elif time >= self.__Settings['Fault end time (sec)']:
            self.__FaultObj.SetParameter('enabled', 'no')
        return 0



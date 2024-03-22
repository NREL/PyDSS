from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract

class FaultController(ControllerAbstract):
    """The class is used to induce faults on bus for dynamic simulation studies. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class. 

    :param FaultObj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type FaultObj: class:`pydss.dssElement.dssElement`
    :param Settings: A dictionary that defines the settings for the faul controller.
    :type Settings: dict
    :param dssInstance: An :class:`opendssdirect` instance
    :type dssInstance: :class:`opendssdirect` instance
    :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit ojects
    :type ElmObjectList: dict
    :param dssSolver: An instance of one of the classes defined in :mod:`pydss.SolveMode`.
    :type dssSolver: :mod:`pydss.SolveMode`
    :raises: AssertionError  if 'FaultObj' is not a wrapped OpenDSS Fault element

    """
    def __init__(self, FaultObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Constructor method
        """

        super(FaultController, self).__init__(FaultObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.P_old = 0
        self.Time = -1
        self.__Locked = False
        self.__dssSolver = dssSolver
        self.__FaultObj = FaultObj
        self.__FaultEnabled = False
        self.__Settings = Settings
        nPhases = len(Settings['Bus1'].split('.')) - 1
        FaultObj.SetParameter('bus1', Settings['Bus1'])
        FaultObj.SetParameter('bus2', Settings['Bus2'])
        FaultObj.SetParameter('phases', nPhases)
        FaultObj.SetParameter('r', Settings['Fault resistance'])
        self.__Class, Name = self.__FaultObj.GetInfo()
        assert (self.__Class.lower() == 'fault'), 'FaultController works only with an OpenDSS Fault element'
        self.__Name = 'pyCont_' + self.__Class + '_' + Name
        self.__init_time = dssSolver.GetDateTime()
        self.__Settings['Fault end time (sec)'] = self.__Settings['Fault start time (sec)'] + \
                                                  self.__Settings['Fault duration (sec)']
        return

    def Update(self, Priority, Time, UpdateResults):
        """Induces and removes a fault as the simulation runs as per user defined settings. 
        """
        time = self.__dssSolver.GetTotalSeconds() - self.__dssSolver.GetStepSizeSec()
        self.__FaultObj.SetParameter('enabled', 'yes')
        if time >= self.__Settings['Fault start time (sec)'] and time < self.__Settings['Fault end time (sec)'] and\
            self.__FaultEnabled==False:
            self.__FaultObj.SetParameter('enabled', 'yes')
            self.__FaultEnabled = True
        elif time >= self.__Settings['Fault end time (sec)'] and self.__FaultEnabled==True:
            self.__FaultObj.SetParameter('enabled', 'no')
            self.__FaultEnabled = False
        return 0
        
    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.__Class, self.__Name)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]




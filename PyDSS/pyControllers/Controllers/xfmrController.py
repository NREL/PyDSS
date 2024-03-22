from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract

class xfmrController(ControllerAbstract):
    """The controller locks a regulator in the event of reverse power flow. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

                :param RegulatorObj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'Regulator' element
                :type FaultObj: class:`pydss.dssElement.dssElement`
                :param Settings: A dictionary that defines the settings for the PvController.
                :type Settings: dict
                :param dssInstance: An :class:`opendssdirect` instance
                :type dssInstance: :class:`opendssdirect`
                :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
                :type ElmObjectList: dict
                :param dssSolver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
                :type dssSolver: :mod:`pydss.SolveMode`
                :raises: AssertionError if 'RegulatorObj' is not a wrapped OpenDSS Regulator element

        """

    def __init__(self, RegulatorObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(xfmrController).__init__(RegulatorObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.P_old = 0
        self.Time = -1
        self.__Locked = False
        self.__ControlledElm = RegulatorObj
        self.__ConnTransformerName = 'Transformer.' + self.__ControlledElm.GetParameter('transformer').lower()
        self.__ConnTransformer = ElmObjectList[self.__ConnTransformerName]
        self.__ElmObjectList = ElmObjectList
        self.__RPFlocking = Settings['RPF locking']
        Class, Name = self.__ControlledElm.GetInfo()

        self.__Name = 'pyCont_' + Class + '_' + Name
        return

    @property
    def Name(self):
        return self.__Name

    @property
    def ControlledElement(self):
        return "{}.{}".format(self.Class, self.Name)

    def Update(self, Priority, Time, UpdateResults):
        Powers = self.__ConnTransformer.GetVariable('CurrentsMagAng')
        Powers = Powers[:int(len(Powers)/2)][::2]
        P_new = sum((float(x)) for x in Powers)
        if self.__RPFlocking and self.P_old < 0:
            self.__Locked = self.__EnableLock()
        elif self.__RPFlocking and self.P_old > 0:
            self.__Locked = self.__DisableLock()
        else:
            pass
        self.P_old = P_new
        return 0

    def __EnableLock(self):
        self.__ControlledElm.SetParameter('enabled','False')
        return True

    def __DisableLock(self):
        self.__ControlledElm.SetParameter('enabled', 'True')
        return False


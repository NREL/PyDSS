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
    def __init__(self, ctrlObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Constructor method
        """

        super(FaultController, self).__init__(ctrlObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.P_old = 0
        self.Time = -1
        self.dssInstance = dssInstance
        self.ElmObjectList = ElmObjectList
        self._ControlledElm = ctrlObj
        self.__dssSolver = dssSolver
        self.__FaultEnabled = False
        self.__Settings = Settings
        self.bus = self._ControlledElm.sBus[Settings["bus_index"]]
        available_phases = self.bus.Phases[0]
        self._eClass, self._eName = self._ControlledElm.GetInfo()
        
        
        
        for t in Settings["terminal_a"]:
            assert t in available_phases, f"Termal {t} does not exist for bus {self.bus.Name}"

        T1 = ".".join([str(x) for x in Settings["terminal_a"]])
        if Settings["terminal_b"]:
            T2 = ".".join([str(x) for x in Settings["terminal_b"]])
            cmd = f"New Fault.{Settings['FID']} phases={len( Settings['terminal_a'])}  Bus1={self.bus.Name}.{T1} Bus2={self.bus.Name}.{T2} r={Settings['Fault resistance']} enabled=no"
        else:
            cmd = f"New Fault.{Settings['FID']} phases={len( Settings['terminal_a'])}  Bus1={self.bus.Name}.{T1} r={Settings['Fault resistance']} enabled=no"
        reply = dssInstance.utils.run_command(cmd)
        assert not reply, f"Error creating fault object: {reply}"
        self.fault_name = f"Fault.{Settings['FID']}"
       
        self.__Class = "Fault"
        Name = Settings['FID']

        self.__Name = 'pyCont_' + self.__Class + '_' + Name
        self.__Settings['Fault end time (sec)'] = self.__Settings['Fault start time (sec)'] + self.__Settings['Fault duration (sec)']

        return

    def Update(self, Priority, Time, UpdateResults):
        if Priority == 0:
            time = self.__dssSolver.GetTotalSeconds() - self.__dssSolver.GetStepSizeSec()
            #self.enable_fault()
            if time >= self.__Settings['Fault start time (sec)'] and time < self.__Settings['Fault end time (sec)'] and\
                self.__FaultEnabled==False:
                self.enable_fault()
                self.__FaultEnabled = True
            elif time >= self.__Settings['Fault end time (sec)'] and self.__FaultEnabled==True:
                self.disable_fault()
                self.__FaultEnabled = False
            
            if time >= self.__Settings['Fault end time (sec)']:
                obj = self.ElmObjectList["Vsource.source"]
                obj.SetParameter("pu", obj.GetParameter("pu") * 0.999)
                print(f"Voltage: {obj.GetParameter('pu')} pu")
            
        return 0

        
    def enable_fault(self):
        cmd = f"{self.fault_name}.enabled=True"
        reply = self.dssInstance.utils.run_command(cmd)
        assert not reply, f"Error creating fault object: {reply}"
        print(cmd, reply)
        return
    
    def disable_fault(self):
        cmd = f"{self.fault_name}.enabled=False"
        reply = self.dssInstance.utils.run_command(cmd)
        assert not reply, f"Error creating fault object: {reply}"
        print(cmd, reply)
        return
        
    def Name(self):
        return self.Name

    def ControlledElement(self):
        return "{}.{}".format(self._eClass, self._eName)
    
    def debugInfo(self):
        return [self._Settings['Control{}'.format(i+1)] for i in range(3)]
    




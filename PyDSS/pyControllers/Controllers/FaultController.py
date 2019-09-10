from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract

class FaultController(ControllerAbstract):
    P_old = 0
    Time = -1

    __Locked = False
    def __init__(self, FaultObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(FaultController).__init__()
        self.__dssSolver = dssSolver
        self.__FaultObj = FaultObj
        self.__Settings = Settings
        FaultObj.SetParameter('bus1', Settings['Bus1'])
        FaultObj.SetParameter('bus2', Settings['Bus2'])
        FaultObj.SetParameter('r', Settings['Fault resistance'])
        print(FaultObj, Settings)
        Class, Name = self.__FaultObj.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        self.__init_time = dssSolver.GetDateTime()
        self.__Settings['Fault end time (sec)'] = self.__Settings['Fault start time (sec)'] + \
                                                  self.__Settings['Fault duration (sec)']
        return

    def Update(self, Priority, Time, UpdateResults):
        time = (self.__dssSolver.GetDateTime() - self.__init_time).total_seconds()

        if time >= self.__Settings['Fault start time (sec)'] and time < self.__Settings['Fault end time (sec)']:
            self.__FaultObj.SetParameter('enabled', 'yes')
        elif time >= self.__Settings['Fault end time (sec)']:
            self.__FaultObj.SetParameter('enabled', 'no')
        return 0

    # def __EnableLock(self):
    #     self.__ControlledElm.SetParameter('enabled','False')
    #     return True
    #
    # def __DisableLock(self):
    #     self.__ControlledElm.SetParameter('enabled', 'True')
    #     #self.__ControlledElm.SetParameter('enabled', 'False')
    #     return False


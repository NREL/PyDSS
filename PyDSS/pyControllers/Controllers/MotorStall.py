#Algebraic model for Type D motor - Residential air conditioner
'''
author: Kapil Duwadi
Version: 1.0
'''

from PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import random
import math

class MotorStall(ControllerAbstract):
    """The controller locks a regulator in the event of reverse power flow. Subclass of the :class:`PyDSS.pyControllers.
    pyControllerAbstract.ControllerAbstract` abstract class.

                :param RegulatorObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Regulator' element
                :type FaultObj: class:`PyDSS.dssElement.dssElement`
                :param Settings: A dictionary that defines the settings for the PvController.
                :type Settings: dict
                :param dssInstance: An :class:`opendssdirect` instance
                :type dssInstance: :class:`opendssdirect`
                :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
                :type ElmObjectList: dict
                :param dssSolver: An instance of one of the classed defined in :mod:`PyDSS.SolveMode`.
                :type dssSolver: :mod:`PyDSS.SolveMode`
                :raises: AssertionError if 'RegulatorObj' is not a wrapped OpenDSS Regulator element

        """


    def __init__(self, MotorObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(MotorStall, self).__init__(MotorObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self._class, self._name = MotorObj.GetInfo()
        self.name = "Controller-{}-{}".format(self._class, self._name)
        self._ControlledElm = MotorObj
        self.__Settings = Settings
        self.__dssSolver = dssSolver

        self._ControlledElm.SetParameter('model', 2)
        self._ControlledElm.SetParameter('vminpu', 0.0)

        self.kw = self.__Settings['ratedKW']
        S = self.kw / self.__Settings['ratedPF']
        self.kvar = math.sqrt(S**2 - self.kw**2)
        self._ControlledElm.SetParameter('kw', self.kw)
        self._ControlledElm.SetParameter('kvar', self.kvar)
        self.stall_time_start = 0
        self.stall = False
        self.disconnected =False
        self.Tdisconnect_start = 0
        return


    def Name(self):
        return self.name

    def ControlledElement(self):
        return "{}.{}".format(self._class, self._name)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]


    def Update(self, Priority, Time, UpdateResults):
        if Priority == 0:
            Vbase = self._ControlledElm.sBus[0].GetVariable('kVBase')
            Ve_mags = max(self._ControlledElm.GetVariable('VoltagesMagAng')[::2])/ 120.0

            if Ve_mags < self.__Settings['Vstall'] and not self.stall:
                self._ControlledElm.SetParameter('kw', self.kw * self.__Settings['Pfault'])
                self._ControlledElm.SetParameter('kvar', self.kw * self.__Settings['Qfault'])
                self._ControlledElm.SetParameter('model', 1)
                self.stall = True
                self.stall_time_start = self.__dssSolver.GetTotalSeconds()
                return 0.1
            return 0
        if Priority == 1:
            if self.stall:
                self.stall_time = self.__dssSolver.GetTotalSeconds() - self.stall_time_start
                if self.stall_time > self.__Settings['Tprotection']:
                    self.stall = False
                    self.disconnected = True
                    self._ControlledElm.SetParameter('kw', 0)
                    self._ControlledElm.SetParameter('kvar', 0)
                    self.Tdisconnect_start = self.__dssSolver.GetTotalSeconds()
                return 0
            return 0
        if Priority == 2:
            if self.disconnected:
                time = self.__dssSolver.GetTotalSeconds() - self.Tdisconnect_start
                if time > self.__Settings['Treconnect']:
                    self.disconnected = False
                    self._ControlledElm.SetParameter('kw', self.kw)
                    self._ControlledElm.SetParameter('kvar', self.kvar)
                    self._ControlledElm.SetParameter('model', 2)
                    self._ControlledElm.SetParameter('vminpu', 0.0)

        return 0


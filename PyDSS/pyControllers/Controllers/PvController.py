from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import math
import abc
from collections import namedtuple

from PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
from PyDSS.utils.timing_utils import timer_stats_collector, track_timing


VVarSettings = namedtuple("VVarSettings", ["VmeaMethod", "uMin", "uMax", "uDbMin", "uDbMax", "kVBase"])


class PvController(ControllerAbstract):
    """Implementation of smart control modes of modern inverter systems. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

        :param PvObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'PVSystem' element
        :type FaultObj: class:`PyDSS.dssElement.dssElement`
        :param Settings: A dictionary that defines the settings for the PvController.
        :type Settings: dict
        :param dssInstance: An :class:`opendssdirect` instance
        :type dssInstance: :class:`opendssdirect`
        :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type ElmObjectList: dict
        :param dssSolver: An instance of one of the classed defined in :mod:`PyDSS.SolveMode`.
        :type dssSolver: :mod:`PyDSS.SolveMode`
        :raises: AssertionError if 'PvObj' is not a wrapped OpenDSS PVSystem element

    """

    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Constructor method
        """
        super(PvController, self).__init__(PvObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.TimeChange = False
        self.Time = (-1, 0)

        self.oldQpv = 0
        self.oldPcalc = 0

        self.__vDisconnected = False
        self.__pDisconnected = False

        self.__ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None'           : lambda: 0,
            'CPF'            : self.CPFcontrol,
            'VPF'            : self.VPFcontrol,
            'VVar'           : self.VVARcontrol,
            'VW'             : self.VWcontrol,
            'Cutoff'         : self.CutoffControl,
        }

        self.__ControlledElm = PvObj
        self.ceClass, self.ceName = self.__ControlledElm.GetInfo()

        assert (self.ceClass.lower()=='pvsystem'), 'PvController works only with an OpenDSS PVSystem element'
        self.__Name = 'pyCont_' + self.ceClass + '_' +  self.ceName
        if '_' in  self.ceName:
            self.Phase =  self.ceName.split('_')[1]
        else:
            self.Phase = None
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = PvObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.__BaseKV = float(PvObj.GetParameter('kv'))
        self.__Srated = float(PvObj.GetParameter('kVA'))
        self.__Prated = float(PvObj.GetParameter('Pmpp'))
        self.__Qrated = float(PvObj.GetParameter('kvarMax'))
        self.__cutin = float(PvObj.SetParameter('%cutin', 0)) / 100
        self.__cutout = float(PvObj.SetParameter('%cutout', 0)) / 100
        self.__dampCoef = Settings['DampCoef']

        self.__PFrated = Settings['PFlim']
        self.Pmppt = 100
        self.pf = 1

        self.update = []
        self._vvar = None
        if 'VmeaMethod' not in self.__Settings:
            self.__Settings['VmeaMethod'] = "max"
        for i in range(1, 4):
            controller_type = self.__Settings['Control' + str(i)]
            self.update.append(self.ControlDict[controller_type])
            if controller_type == "VVar":
                self._vvar = VVarSettings(
                    VmeaMethod=self.__Settings["VmeaMethod"].lower(),
                    uMin=self.__Settings["uMin"],
                    uMax=self.__Settings["uMax"],
                    uDbMin=self.__Settings["uDbMin"],
                    uDbMax=self.__Settings["uDbMax"],
                    kVBase=self.__ControlledElm.sBus[0].GetVariable('kVBase') * 1000,
                )

        if self.__Settings["Priority"] == "Var":
            PvObj.SetParameter('WattPriority', "False")
        else:
            PvObj.SetParameter('WattPriority', "True")
        #PvObj.SetParameter('VarFollowInverter', "False")

        #self.QlimPU = self.__Qrated / self.__Srated if self.__Qrated < self.__Srated else 1

        self.QlimPU = min(self.__Qrated / self.__Srated, self.__Settings['QlimPU'], 1.0)
        self.itr = 0
        return

    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.ceClass, self.ceName)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]

    @track_timing(timer_stats_collector)
    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = (Priority, Time)
        Ppv = -sum(self.__ControlledElm.GetVariable('Powers')[::2]) / self.__Prated

        if self.TimeChange:
            self.itr = 0
        else:
            self.itr += 1

        if self.__pDisconnected:
            if Ppv < self.__cutin:
                return 0
            else:
                self.__pDisconnected = False
        else:
            if Ppv < self.__cutout:
                self.__pDisconnected = True
                self.__ControlledElm.SetParameter('pf', 1)
                return 0
        return self.update[Priority]()

    @track_timing(timer_stats_collector)
    def VWcontrol(self):
        """Volt / Watt  control implementation
        """
        uMinC = self.__Settings['uMinC']
        uMaxC = self.__Settings['uMaxC']
        Pmin  = self.__Settings['PminVW'] / 100

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])
        Ppv = -sum(self.__ControlledElm.GetVariable('Powers')[::2]) / self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2]) / self.__Srated


        #PpvoutPU = Ppv / self.__Prated

        Plim = (1 - Qpv ** 2) ** 0.5 if self.__Settings['VWtype'] == 'Available Power' else 1
        m = (1 - Pmin) / (uMinC - uMaxC)
        #m = (Plim - Pmin) / (uMinC - uMaxC)
        c = ((Pmin * uMinC) - uMaxC) / (uMinC - uMaxC)

        if uIn < uMinC:
            Pcalc = Plim
        elif uIn < uMaxC and uIn > uMinC:
            Pcalc = min(m * uIn + c, Plim)
        else:
            Pcalc = Pmin

        if Ppv > Pcalc or (Ppv > 0 and self.Pmppt < 100):
            # adding heavy ball term to improve convergence
            dP = (Ppv - Pcalc) * 0.5 / self.__dampCoef + (self.oldPcalc - Ppv) * 0.1 / self.__dampCoef
            Pcalc = Ppv - dP
            self.Pmppt = min(self.Pmppt * Pcalc / Ppv, 100)
            self.__ControlledElm.SetParameter('%Pmpp', self.Pmppt)
            self.pf = math.cos(math.atan(Qpv / Pcalc))
            if Qpv < 0:
                self.pf = -self.pf
            self.__ControlledElm.SetParameter('pf', self.pf)
        else:
            dP = 0

        Error = abs(dP)
        self.oldPcalc = Ppv
        return Error

    @track_timing(timer_stats_collector)
    def CutoffControl(self):
        """Over voltage trip implementation
        """
        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])
        uCut = self.__Settings['%UCutoff']
        if uIn >= uCut:
            self.__ControlledElm.SetParameter('%Pmpp', 0)
            self.__ControlledElm.SetParameter('pf', 1)
            if self.__vDisconnected:
                return 0
            else:
                self.__vDisconnected = True
                return self.__Prated

        if self.TimeChange and self.__vDisconnected and uIn < uCut:
            self.__ControlledElm.SetParameter('%Pmpp', self.Pmppt)
            self.__ControlledElm.SetParameter('pf', self.pf)
            self.__vDisconnected = False
            return self.__Prated

        return 0

    @track_timing(timer_stats_collector)
    def CPFcontrol(self):
        """Constant power factor implementation
        """
        PFset = self.__Settings['pf']
        PFact = self.__ControlledElm.GetParameter('pf')
        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2])) / self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2]) / self.__Srated

        if self.__Settings['cpf-priority'] == 'PF':
           # if self.TimeChange:
            Plim = PFset * 100
            self.__ControlledElm.SetParameter('%Pmpp', Plim)
           # else:
        else:
            if self.__Settings['cpf-priority'] == 'Var':
                #add code for var priority here
                Plim = 0
            else:
                Plim = 1
            if self.TimeChange:
                self.Pmppt = 100
            else:
                self.Pmppt = Plim  * self.__Srated

        Error = abs(PFset + PFact)
        self.__ControlledElm.SetParameter('pf', str(-PFset))
        return Error

    @track_timing(timer_stats_collector)
    def VPFcontrol(self):
        """Variable power factor control implementation
        """
        Pmin = self.__Settings['Pmin']
        Pmax = self.__Settings['Pmax']
        PFmin = self.__Settings['pfMin']
        PFmax = self.__Settings['pfMax']
        self.__dssSolver.reSolve()
        Pcalc = abs(sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0::2]) ) / self.__Srated
        if Pcalc > 0:
            if Pcalc < Pmin:
                PF = PFmax
            elif Pcalc > Pmax:
                PF = PFmin
            else:
                m = (PFmax - PFmin) / (Pmin - Pmax)
                c = (PFmin * Pmin - PFmax * Pmax) / (Pmin - Pmax)
                PF = Pcalc * m + c
        else:
            PF = PFmax

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', str(-PF))
        self.__dssSolver.reSolve()

        for i in range(10):
            Error = PF + float(self.__ControlledElm.GetParameter('pf'))
            if abs(Error) < 1E-4:
                break
            Pirr = float(self.__ControlledElm.GetParameter('irradiance'))
            self.__ControlledElm.SetParameter('pf', str(-PF))
            self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error*1.5))
            self.__dssSolver.reSolve()

        return 0

    @track_timing(timer_stats_collector)
    def VVARcontrol(self):
        """Volt / var control implementation
        """

        Umag = self.__ControlledElm.GetVariable('VoltagesMagAng')[::2]
        Umag = [i for i in Umag if i != 0]
        vmea = self._vvar.VmeaMethod
        if vmea == "max":
            uIn = max(Umag) / self._vvar.kVBase
        elif vmea.lower() == "mean":
            uIn = sum(Umag) / (len(Umag) * self._vvar.kVBase)
        elif vmea == "min":
            uIn = min(Umag) / self._vvar.kVBase
        elif vmea == "1":
            uIn = Umag[0] / self._vvar.kVBase
        elif vmea == "2":
            uIn = Umag[1] / self._vvar.kVBase
        elif vmea == "3":
            uIn = Umag[3] / self._vvar.kVBase
        else:
            uIn = max(Umag) / self._vvar.kVBase

        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        Pcalc = Ppv / self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2])
        Qpv = Qpv / self.__Srated

        Qcalc = 0
        if uIn <= self._vvar.uMin:
            Qcalc = self.QlimPU
        elif uIn <= self._vvar.uDbMin and uIn > self._vvar.uMin:
            m1 = self.QlimPU / (self._vvar.uMin - self._vvar.uDbMin)
            c1 = self.QlimPU * self._vvar.uDbMin / (self._vvar.uDbMin - self._vvar.uMin)
            Qcalc = uIn * m1 + c1
        elif uIn <= self._vvar.uDbMax and uIn > self._vvar.uDbMin:
            Qcalc = 0
        elif uIn <= self._vvar.uMax and uIn > self._vvar.uDbMax:
            m2 = self.QlimPU / (self._vvar.uDbMax - self._vvar.uMax)
            c2 = self.QlimPU * self._vvar.uDbMax / (self._vvar.uMax - self._vvar.uDbMax)
            Qcalc = uIn * m2 + c2
        elif uIn >= self._vvar.uMax:
            Qcalc = -self.QlimPU

        Qcalc = Qpv + (Qcalc - Qpv) * 0.5 / self.__dampCoef + (Qpv - self.oldQpv) * 0.1 / self.__dampCoef

        if Pcalc > 0:
            if self.__ControlledElm.NumPhases == 2:
                self.__ControlledElm.SetParameter('kvar', Qcalc * self.__Srated * 1.3905768334328491495461135972974)
            else:
                self.__ControlledElm.SetParameter('kvar', Qcalc * self.__Srated)
        else:
            pass

        Error = abs(Qpv- self.oldQpv)
        self.oldQpv = Qpv

        return Error

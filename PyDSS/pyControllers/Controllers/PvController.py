from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import math
import abc

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

        self.oldPcalc = 0
        self.oldQcalc = 0

        self.__vDisconnected = False
        self.__pDisconnected = False

        self.__ElmObjectList = ElmObjectList
        #print(PvObj.Bus[0] + ' - ' + PvObj.sBus[0].GetInfo())
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
        self.__Qrated = float(PvObj.GetParameter('kVARlimit'))
        self.__cutin = float(PvObj.SetParameter('%cutin', Settings['%PCutin'])) / 100
        self.__cutout = float(PvObj.SetParameter('%cutout',Settings['%PCutout'])) / 100
        self.__dampCoef = Settings['DampCoef']

        self.__PFrated = Settings['PFlim']
        self.Pmppt = 100
        self.pf = 1

        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]

        #self.QlimPU = self.__Qrated / self.__Srated if self.__Qrated < self.__Srated else 1
        self.QlimPU = min(self.__Qrated / self.__Srated, Settings['QlimPU'], 1.0)
        return


    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.ceClass, self.ceName)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]

    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = (Priority, Time)
        Ppv = -sum(self.__ControlledElm.GetVariable('Powers')[::2]) / self.__Prated
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
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)
            self.pf = math.cos(math.atan(Qpv / Pcalc))
            if Qpv < 0:
                self.pf = -self.pf
            self.__ControlledElm.SetParameter('pf', self.pf)
        else:
            dP = 0

        Error = abs(dP)
        self.oldPcalc = Ppv
        # if Error > 0.1:
        #     print((self.__Name, uIn, Qpv, Plim, Ppv, Pcalc, self.Pmppt, dP, self.pf))
        return Error

    def CutoffControl(self):
        """Over voltage trip implementation
        """
        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])
        uCut = self.__Settings['%UCutoff']
        if uIn >= uCut:
            self.__ControlledElm.SetParameter('pctPmpp', 0)
            self.__ControlledElm.SetParameter('pf', 1)
            if self.__vDisconnected:
                return 0
            else:
                self.__vDisconnected = True
                # print('Disconnecting {} at voltage {:.2f}'.format(self.__Name, uIn))
                return self.__Prated

        if self.TimeChange and self.__vDisconnected and uIn < uCut:
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)
            self.__ControlledElm.SetParameter('pf', self.pf)
            self.__vDisconnected = False
            # print('Reconnecting {} at voltage {:.2f}'.format(self.__Name, uIn))
            return self.__Prated

        return 0

    def CPFcontrol(self):
        """Constant power factor implementation
        """
        PFset = self.__Settings['pf']
        PFact = self.__ControlledElm.GetParameter('pf')
        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))/ self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2])/ self.__Srated

        if self.__Settings['cpf-priority'] == 'PF':
           # if self.TimeChange:
            Plim = PFset * 100
            self.__ControlledElm.SetParameter('pctPmpp', Plim)
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
            #print(self.Pmppt , self.__Srated)


        Error = abs(PFset + PFact)
        self.__ControlledElm.SetParameter('pf', str(-PFset))
        return Error

    def VPFcontrol(self):
        """Variable power factor control implementation
        """
        Pmin = self.__Settings['Pmin']
        Pmax = self.__Settings['Pmax']
        PFmin = self.__Settings['pfMin']
        PFmax = self.__Settings['pfMax']
        self.__dssSolver.reSolve()
        Pcalc = abs(sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0::2]) )/ self.__Srated
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

    def VVARcontrol(self):
        """Volt / var control implementation
        """
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        pfLim = self.__Settings['PFlim']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        Priority = self.__Settings['Priority']

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])

        m1 = self.QlimPU / (uMin - uDbMin)
        m2 = self.QlimPU / (uDbMax - uMax)
        c1 = self.QlimPU * uDbMin / (uDbMin - uMin)
        c2 = self.QlimPU * uDbMax / (uMax - uDbMax)

        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        Pcalc = Ppv / self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2])
        Qpv = Qpv / self.__Srated

        Qcalc = 0
        if uIn <= uMin:
            Qcalc = self.QlimPU
        elif uIn <= uDbMin and uIn > uMin:
            Qcalc = uIn * m1 + c1
        elif uIn <= uDbMax and uIn > uDbMin:
            Qcalc = 0
        elif uIn <= uMax and uIn > uDbMax:
            Qcalc = uIn * m2 + c2
        elif uIn >= uMax:
            Qcalc = -self.QlimPU

        # adding heavy ball term to improve convergence
        Qcalc = Qpv + (Qcalc - Qpv) * 0.5 / self.__dampCoef + (Qpv - self.oldQcalc) * 0.1 / self.__dampCoef
        dQ = abs(Qcalc - Qpv)

        if Priority == 'Var':
            Plim = (1 - Qcalc ** 2) ** 0.5
            # Pcalc = Pcalc + (Plim - Pcalc) * self.__Settings['qDampCoef']
            # self.Pmppt = Pcalc / self.__Prated * self.__Srated * 100
            if self.TimeChange:
                self.Pmppt = 100
            if Pcalc > Plim and self.TimeChange is False:
                self.Pmppt = Plim / self.__Prated * self.__Srated * 100
                Pcalc = Plim
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)
        else:
            # no watt priority defined yet
            pass

        if Pcalc > 0:
            self.pf = math.cos(math.atan(Qcalc / Pcalc))
            if self.__Settings['Enable PF limit'] and abs(self.pf) < pfLim:
                self.pf = pfLim
            if Qcalc < 0:
                self.pf = -self.pf
            self.__ControlledElm.SetParameter('pf', self.pf)
        else:
            #print('Warning: PV power is <0 and VVar controller is active.')
            #print(self.__Name, Qcalc , Qpv, self.Time, dQ)
            # self.pf = 0
            # dQ = 0 # forces VVarr off when PV is off, is that correct?
            pass

        Error = abs(dQ)
        # if Error > 0.1 or math.isnan(Error):
        #     print((self.__Name, uIn, Qcalc, Qpv, self.oldQcalc, dQ, Pcalc, self.pf, self.__ControlledElm.GetVariable('Powers')))
        self.oldQcalc = Qpv

        return Error

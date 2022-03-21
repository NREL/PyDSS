from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import math

class HybridController(ControllerAbstract):
    TimeChange = False
    Time = (-1, 0)

    oldPcalc = 0
    oldQcalc = 0
    #dPOld = 0
    #dQOld = 0

    __vDisconnected = False
    __pDisconnected = False

    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(HybridController).__init__(PvObj, Settings, dssInstance, ElmObjectList, dssSolver)
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
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        if '_' in Name:
            self.Phase = Name.split('_')[1]
        else:
            self.Phase = None
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = PvObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]

        return

    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = (Priority, Time)
        # Ppv = -sum(self.__ControlledElm.GetVariable('Powers')[::2]) / self.__Prated
        # if self.__pDisconnected:
        #     if Ppv < self.__cutin:
        #         return 0
        #     else:
        #         self.__pDisconnected = False
        # else:
        #     if Ppv < self.__cutout:
        #         self.__pDisconnected = True
        #         self.__ControlledElm.SetParameter('pf', 1)
        #         return 0
        return self.update[Priority]()

    def VWcontrol(self):
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

    def CutoffControl(self):
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


    def CPFcontrol(self):
        PF = self.__Settings['pf']
        self.__dssSolver.reSolve()

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', -PF)

        Error = PF + float(self.__ControlledElm.GetParameter('pf'))

        Pirr = float(self.__ControlledElm.GetParameter('irradiance'))
        self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error * 3))
        self.__ControlledElm.SetParameter('pf', str(-PF))

        return Error

    def VPFcontrol(self):
        Pmin = self.__Settings['Pmin']
        Pmax = self.__Settings['Pmax']
        PFmin = self.__Settings['pfMin']
        PFmax = self.__Settings['pfMax']
        self.__dssSolver.reSolve()
        Pcalc = abs(sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0::2])) / self.__Srated
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
            if self.TimeChange:
                self.Pmppt = 100
            if Pcalc > Plim and self.TimeChange is False:
                self.Pmppt = Plim / self.__Prated * self.__Srated * 100
                Pcalc = Plim
            self.__ControlledElm.SetParameter('%Pmpp', self.Pmppt)
        else:
            pass

        if Pcalc > 0:
            self.pf = math.cos(math.atan(Qcalc / Pcalc))
            if self.__Settings['Enable PF limit'] and abs(self.pf) < pfLim:
                self.pf = pfLim
            if Qcalc < 0:
                self.pf = -self.pf
            self.__ControlledElm.SetParameter('pf', self.pf)
        else:
            pass

        Error = abs(dQ)
        self.oldQcalc = Qpv

        return Error

import matplotlib.pyplot as plt
import math

class PvController:
    TimeChange = False
    Time = 0

    oldPcalc = 0
    oldQcalc = 0
    dPOld = 0
    dQOld = 0

    __Disconnected = False

    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.__ElmObjectList = ElmObjectList
        #print(PvObj.Bus[0] + ' - ' + PvObj.sBus[0].GetInfo())
        self.P_ControlDict = {
            'None'           : lambda: 0,
            'VW'             : self.VWcontrol,}

        self.Q_ControlDict = {
            'None'           : lambda: 0,
            'Cutoff'         : self.CutoffControl,
            'CPF'            : self.CPFcontrol,
            'VPF'            : self.VPFcontrol,
            'VVar'           : self.VVARcontrol, }

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

        self.__BaseKV = float(PvObj.GetParameter2('kv'))
        self.__Srated = float(PvObj.GetParameter2('kVA'))
        self.__Prated = float(PvObj.GetParameter2('Pmpp'))
        self.__Qrated = float(PvObj.GetParameter2('kVARlimit'))
        self.__cutin = PvObj.SetParameter('%cutin', Settings['%PCutin'])
        self.__cutout = PvObj.SetParameter('%cutout',Settings['%PCutout'])
        self.__Ucutoff = Settings['%UCutoff']
        self.__enableCutoff = Settings['Enable Cutoff']

        self.__PFrated = Settings['PFlim']
        self.Pmppt = 100

        self.P_update = self.P_ControlDict[Settings['Pcontrol']]
        self.Q_update = self.Q_ControlDict[Settings['Qcontrol']]

        self.QlimPU = self.__Qrated / self.__Srated if self.__Qrated < self.__Srated else 1
        return

    def Update_Q(self, Time, Update):
        if Time >= 1:
            if self.Time != Time:
                self.TimeChange = True
            else:
                self.TimeChange = False
            self.Time = Time

            self.doUpdate = Update
            dQ = self.Q_update()
        else:
            dQ = 0
        return dQ

    def Update_P(self, Time, Update):
        if Time >= 1:
            self.Time = Time
            self.doUpdate = Update
            dP = self.P_update()
        else:
            dP = 0
        self.p = dP
        return self.p

    def VWcontrol(self):
        DampCoef = self.__Settings['pDampCoef']
        uMinC = self.__Settings['uMinC']
        uMaxC = self.__Settings['uMaxC']
        Pmin  = self.__Settings['PminVW'] / 100

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])
        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        Qpv = abs(sum(self.__ControlledElm.GetVariable('Powers')[1::2]))
        PpvoutPU= Ppv / self.__Prated
        Plim = (1 - (Qpv / self.__Srated)**2) ** 0.5
        m = (1 - Pmin) / (uMinC - uMaxC)
        #m = (Plim - Pmin) / (uMinC - uMaxC)
        c = ((Pmin * uMinC) - uMaxC) / (uMinC - uMaxC)

        if uIn < uMinC:
            #Pmax = 1
            Pmax = Plim
        elif uIn < uMaxC and uIn > uMinC:
            Pmax = min(m * uIn + c, Plim)
        else:
            Pmax = Pmin

        pctPmpp = self.__ControlledElm.GetValue('pctPmpp')

        if self.__Settings['VWtype'] == 'Rated Power':
            Pcalc = Pmax * 100
            dP = (pctPmpp - Pcalc) * DampCoef
            Pcalc = pctPmpp - dP
            Pcalc = self.Pmppt if Pcalc > self.Pmppt else Pcalc

        elif self.__Settings['VWtype'] == 'Available Power':
            Pcalc = Pmax * PpvoutPU * 100
            dP = (pctPmpp - Pcalc) * DampCoef
            Pcalc = pctPmpp - dP
            Pcalc = self.Pmppt if Pcalc > self.Pmppt else Pcalc

        self.__ControlledElm.SetParameter('pctPmpp', Pcalc)
        PFout = -math.cos(math.atan(self.oldQcalc / Pmax))
        self.__ControlledElm.SetParameter('pf', str(PFout))
        Error = abs(dP - self.dPOld)
        self.oldPcalc = Pcalc
        self.dPOld = dP

        return Error

    def CutoffControl(self, uIn=None, error=0):
        if not self.__enableCutoff:
            return error
        if uIn is None:
            uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])

        if uIn >= self.__Ucutoff:
            self.__ControlledElm.SetParameter('pctPmpp', 0)
            self.__ControlledElm.SetParameter('pf', 1)
            if self.__Disconnected:
                return 0
            else:
                self.__Disconnected = True
                return error + self.__Prated

        if self.TimeChange and self.__Disconnected and uIn < self.__Ucutoff:
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)
            self.__ControlledElm.SetParameter('pf', 1)
            self.__Disconnected = False
            return error + self.__Prated

        if self.__Disconnected:
            self.__ControlledElm.SetParameter('pctPmpp', 0)
            self.__ControlledElm.SetParameter('pf', 1)
            return 0
        else:
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)
            self.__ControlledElm.SetParameter('pf', 1)
            return error


    def CPFcontrol(self):
        PF = self.__Settings['pf']
        self.__dssSolver.reSolve()

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', -PF)

        Error = PF + float(self.__ControlledElm.GetParameter2('pf'))

        Pirr = float(self.__ControlledElm.GetParameter2('irradiance'))
        self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error * 3))
        self.__ControlledElm.SetParameter('pf', str(-PF))

        if self.__enableCutoff:
            Error = self.CutoffControl(error=Error)
        return Error

    def VPFcontrol(self):
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
            Error =  PF + float(self.__ControlledElm.GetParameter2('pf'))
            if abs(Error) < 1E-4:
                break
            Pirr = float(self.__ControlledElm.GetParameter2('irradiance'))
            self.__ControlledElm.SetParameter('pf', str(-PF))
            self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error*1.5))
            self.__dssSolver.reSolve()

        if self.__enableCutoff:
            Error = self.CutoffControl(error=Error)
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

        Qcalc = 0
        if uIn <= uMin:
            Qcalc = self.QlimPU
        elif uIn <= uDbMin and uIn > uMin:
            Qcalc = uIn * m1 + c1
            Qcalc = self.oldQcalc + (Qcalc - self.oldQcalc) * self.__Settings['qDampCoef']
        elif uIn <= uDbMax and uIn > uDbMin:
            Qcalc = 0
            Qcalc = self.oldQcalc + (Qcalc - self.oldQcalc) * self.__Settings['qDampCoef']
        elif uIn <= uMax and uIn > uDbMax:
            Qcalc = uIn * m2 + c2
            Qcalc = self.oldQcalc + (Qcalc - self.oldQcalc) * self.__Settings['qDampCoef']
        elif uIn >= uMax:
            Qcalc = -self.QlimPU

        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        Pcalc = Ppv / self.__Srated

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

        if Pcalc > 0:
            PFout = -math.cos(math.atan(Qcalc / Pcalc))
            if self.__Settings['Enable PF limit'] and abs(PFout) < pfLim:
                PFout = -pfLim
        else:
            PFout = 1
        self.__ControlledElm.SetParameter('pf', str(PFout))

        dQ = (Qcalc - self.oldQcalc)
        Error = abs(dQ - self.dQOld)
        self.oldQcalc = Qcalc
        self.dQOld = dQ

        # if self.Time == 47 and self.__Name == 'pyCont_' + 'PVSystem' + '_' + 'oh_261584_1_3':
        #     print(locals())
        #     print(self.Pmppt)
        #     print(self.__Prated)
        #     print(self.__Qrated)
        #     print(self.__Srated)

        # print(Error)
        if self.__enableCutoff:
            Error = self.CutoffControl(uIn, Error)
        return Error

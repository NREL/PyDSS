import matplotlib.pyplot as plt
import math

class PvController:
    Time = 0
    TimeChange = False
    dPoutOld = 0
    oldQcalc = 0


    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.__ElmObjectList = ElmObjectList
        #print(PvObj.Bus[0] + ' - ' + PvObj.sBus[0].GetInfo())
        self.P_ControlDict = {
            'None'           : lambda: 0,
            'VW'             : self.VWcontrol,}

        self.Q_ControlDict = {
            'None'           : lambda: 0,
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
        self.__cutin = PvObj.SetParameter('%cutin', Settings['%Cutin'])
        self.__cutout = PvObj.SetParameter('%cutout',Settings['%Cutout'])

        self.__PFrated = Settings['PFlim']

        self.P_update = self.P_ControlDict[Settings['Pcontrol']]
        self.Q_update = self.Q_ControlDict[Settings['Qcontrol']]

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
        return dP

    def VWcontrol(self):
        DampCoef = self.__Settings['pDampCoef']
        uMinC = self.__Settings['uMinC']
        uMaxC = self.__Settings['uMaxC']
        Pmin  = self.__Settings['PminVW'] / 100

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle'))
        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        PpvoutPU= Ppv / self.__Prated
        m = (1 - Pmin) / (uMinC - uMaxC)
        c = ((Pmin * uMinC) - uMaxC) / (uMinC - uMaxC)

        if uIn < uMinC:
            Pmax = 1
        elif uIn < uMaxC and uIn > uMinC:
            Pmax = m * uIn + c
        else:
            Pmax = Pmin

        pctPmpp = self.__ControlledElm.GetValue('pctPmpp')
        if self.__Settings['VWtype'] == 'Rated Power':
            Pout = Pmax * 100
            dP = (pctPmpp - Pout) * DampCoef
            Pout = pctPmpp - dP
        elif self.__Settings['VWtype'] == 'Available Power':
            Pout = Pmax * PpvoutPU * 100
            dP = (pctPmpp - Pout) * DampCoef
            Pout = pctPmpp - dP
        self.__ControlledElm.SetParameter('pctPmpp', Pout)
        PFout = -math.cos(math.atan(self.oldQcalc / Pmax))
        self.__ControlledElm.SetParameter('pf', str(PFout))
        Error = abs(dP - self.dPoutOld)
        self.oldPout = dP
        return Error

    def CPFcontrol(self):
        PF = self.__Settings['pf']
        self.__dssSolver.reSolve()

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', -PF)

        Error = PF + float(self.__ControlledElm.GetParameter2('pf'))

        Pirr = float(self.__ControlledElm.GetParameter2('irradiance'))
        self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error * 3))
        self.__ControlledElm.SetParameter('pf', str(-PF))

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
        return 0

    def VVARcontrol(self):
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        Priority = self.__Settings['Priority']
        QlimPU = self.__Qrated / self.__Srated if self.__Qrated < self.__Srated else 1

        uIn = self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[0]

        m1 = QlimPU / (uMin - uDbMin)
        m2 = QlimPU / (uDbMax - uMax)
        c1 = QlimPU * uDbMin / (uDbMin - uMin)
        c2 = QlimPU * uDbMax / (uMax - uDbMax)

        Qcalc = 0
        if uIn <= uMin:
            Qcalc = QlimPU
        elif uIn <= uDbMin and uIn > uMin:
            Qcalc = uIn * m1 + c1
        elif uIn <= uDbMax and uIn > uDbMin:
            Qcalc = 0
        elif uIn <= uMax and uIn > uDbMax:
            Qcalc = uIn * m2 + c2
        elif uIn >= uMax:
            Qcalc = -QlimPU

        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        Pcalc = Ppv / self.__Srated
        Ppu = Ppv / self.__Prated

        if Priority == 'Var':
            Plim = (1 - Qcalc**2)**0.5
            if Pcalc > Plim and self.TimeChange is False:
                self.Pmppt = Plim / Pcalc * Ppu * 100
                Pcalc = Plim
            else :
                if self.TimeChange:
                    self.Pmppt = 100
            self.__ControlledElm.SetParameter('pctPmpp', self.Pmppt)

        Qcalc = self.__Settings['qDampCoef'] * Qcalc
        if Pcalc > 0:
            PFout = -math.cos(math.atan(Qcalc / Pcalc))
        else:
            PFout = 1
        self.__ControlledElm.SetParameter('pf', str(PFout))


        Error = abs(Qcalc - self.oldQcalc)
        self.oldQcalc = Qcalc
        #print(Error)
        return Error

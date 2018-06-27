import math

class StorageController:
    Time = -1

    def __init__(self, StorageObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.Time = (-1, 0)
        self.__Pin = 0
        self.Pbatt = 0
        self.__PinOld = 0
        self.PbattOld = 0
        self.oldQcalc = 0
        self.ExportOld = False
        self.__ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None' : lambda : 0,
            'PS'   : self.PeakShavingControl,
            'CF'   : self.CapacityFirmimgControl,
            'TT'   : self.TimeTriggeredControl,
            'RT'   : self.RealTimeControl,
            'SH'   : self.ScheduledControl,
            'NETT' : self.NonExportTimeTriggered,
            'CPF'  : self.ConstantPowerFactorControl,
            'VPF'  : self.VariablePowerFactorControl,
            'VVar' : self.VoltVarControl,
        }

        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = StorageObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings
        self.__Srated = float(StorageObj.GetParameter2('kVA'))
        self.__Prated = float(StorageObj.GetParameter2('kWrated'))
        self.__Pbatt = float(StorageObj.GetParameter2('kW'))
        self.__dampCoef = Settings['DampCoef']
        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]

        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        #self.__Convergance = np.zeros((1440,10))
        return

    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Time, Priority)
        self.Time = (Time, Priority)
        return self.update[Priority]()

    def SetSetting(self, Property, Value):
        self.__Settings[Property] = Value
        return

    def GetSetting(self, Property):
        return self.__Settings[Property]

    def ScheduledControl(self):
        P_profile = self.__Settings['Schedule']
        Days = self.__Settings['Days']
        LenSchedule = len(P_profile)
        TotalSeconds = 24*60*60*Days
        TimeStepPerSample = int(TotalSeconds / LenSchedule)

        CurrentTime = int(self.__dssInstance.Solution.Hour()) * 60 * 60 + \
                      int(self.__dssInstance.Solution.Seconds())

        Index =  int(CurrentTime / TimeStepPerSample)
        Pout = P_profile[Index]
        if Pout > 0:
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(Pout * 100))
        elif Pout < 0:
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(-Pout * 100))
        else:
            self.__ControlledElm.SetParameter('State', 'IDLE')
        return 0

    def NonExportTimeTriggered(self):
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin1 = self.__dssInstance.Circuit.TotalPower()
            Pin1 = -sum(Sin1[::2])
        else:
            Sin1 = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin1 = sum(Sin1[::2])

        if self.Time[0] == 0:
            self.dummy = 1 if Pin1 > 0 else -1

        Plb = self.__Settings['BaseLoadLim']
        KWHrated = float(self.__ControlledElm.GetParameter2('kWhrated'))
        perIdle = float(self.__ControlledElm.GetParameter2('%IdlingkW'))
        effDchg = float(self.__ControlledElm.GetParameter2('%EffDischarge'))
        # perDischarge = self.__Settings['%DischargeRate']

        sTime = self.__Settings['ExpWindowStart']
        sTime = sTime.hour + sTime.minute / 60
        eTime = self.__Settings['ExpWindowEnd']
        eTime = eTime.hour + eTime.minute / 60

        currTime = self.__dssInstance.Solution.Hour() % 24 + self.__dssInstance.Solution.Seconds() / 3600

        if sTime < eTime:
            Twindow = (eTime - sTime)
            if currTime > sTime and currTime < eTime:
                Export = True
            else:
                Export = False
        else:
            Twindow = 24 - (sTime - eTime)
            if currTime > sTime or currTime < eTime:
                Export = True
            else:
                Export = False

        if self.ExportOld is False and Export is True:
            perKWHstored = float(self.__ControlledElm.GetParameter2('%stored'))
            kWhrem = KWHrated * (perKWHstored / 100)
            self.Pbatt = kWhrem / (Twindow) * effDchg / 100 - perIdle * self.__Prated / 100
            # print(perKWHstored, kWhrem, self.Pbatt)
        self.ExportOld = Export

        if Export:
            pctcharge = self.Pbatt / (self.__Prated) * 100
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctcharge))
            Error = 0
        else:
            if self.__Settings['PowerMeaElem'] == 'Total':
                Sin = self.__dssInstance.Circuit.TotalPower()
                Pin = -sum(Sin[::2])
            else:
                Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
                Pin = self.dummy * sum(Sin[::2])

            # Pbatt = -float(self.__ControlledElm.GetVariable('Powers')[0])*3 + IdlingkW
            # #Does not work as well as KW parameter for some reason
            Pbatt = float(self.__ControlledElm.GetParameter2('kw'))
            Pb0 = Pbatt
            if Pin < Plb:
                dP = Pin - Plb
                Pbatt = Pbatt + dP
            else:
                dP = Pin - Plb
                Pbatt = min(0, Pbatt + dP * self.__dampCoef)
            if math.isnan(Pbatt) or Pbatt is None:
                print('Error in Pbatt, data: {}'.format((Pbatt, Pin, dP, Plb, Pb0, self.dummy)))

            if Pbatt >= 0:
                pctdischarge = Pbatt / (self.__Prated) * 100
                self.__ControlledElm.SetParameter('State', 'DISCHARGING')
                self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
            if Pbatt < 0:
                pctcharge = -Pbatt / (self.__Prated) * 100
                self.__ControlledElm.SetParameter('State', 'CHARGING')
                self.__ControlledElm.SetParameter('%charge', str(pctcharge))

            Error = abs(Pbatt - self.PbattOld) / self.__Srated
            self.PbattOld = Pbatt
            # if Error > 0.2:
            #     # print((self.__ControlledElm.GetInfo()[1], self.__Settings['PowerMeaElem'], Pin, Pb0, Pbatt))
            #     print((self.__Name, currTime, Pbatt, self.PbattOld, Pin, Plb, dP, Pb0))
        return Error

    def PeakShavingControl(self):
        Pub = self.__Settings['PS_ub']
        Plb = self.__Settings['PS_lb']
        IdlingkWPercent = float(self.__ControlledElm.GetParameter2('%IdlingkW'))
        IdlingkW = -IdlingkWPercent/100*self.__Prated
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:5:2])
        #Pbatt = -float(self.__ControlledElm.GetVariable('Powers')[0])*3 + IdlingkW
        #Does not work as well as KW parameter for come reason
        Pbatt = float(self.__ControlledElm.GetParameter2('kw'))
        if Pin > Pub:
            dP = Pin - Pub
            Pbatt = Pbatt + dP * self.__dampCoef
        elif Pin < Plb:
            dP = Pin - Plb
            Pbatt = Pbatt + dP * self.__dampCoef
        else:
            Pbatt = Pbatt

        if Pbatt >= 0:
            pctdischarge = min(100, Pbatt/ (self.__Prated)* 100)
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))

        elif Pbatt < 0:
            pctcharge = min(100, -Pbatt / (self.__Prated)* 100)
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))

        Error = abs(Pbatt - self.PbattOld) / self.__Srated
        self.PbattOld = Pbatt
        # if Error > 0.2:
        #     print((self.__Name, Pbatt, self.PbattOld, self.__Prated, Pin, Plb, Pub, dP))
        return Error

    def RealTimeControl(self):
        kWOut = self.__Settings['%kWOut']
        if kWOut > 0:
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(kWOut))
        elif kWOut < 0:
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(-kWOut))
        else:
            self.__ControlledElm.SetParameter('State', 'IDLE')
        return 0

    def TimeTriggeredControl(self):
        HrCharge = self.__Settings['HrCharge']
        HrDischarge = self.__Settings['HrDischarge']
        rateCharge = self.__Settings['%rateCharge']
        rateDischarge = self.__Settings['%rateDischarge']

        HrC = int(HrCharge)
        MnC = int((HrCharge - HrC) * 60)
        HrD = int(HrDischarge)
        MnD = int((HrDischarge - HrD) * 60)

        Minutes = int(self.__dssInstance.Solution.Seconds()/60)
        Hour = self.__dssInstance.Solution.Hour()
        if Hour == HrC and Minutes == MnC:
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(rateCharge))
        elif Hour == HrD and Minutes == MnD:
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(rateDischarge))
        return 0

    def CapacityFirmimgControl(self):
        dPub = self.__Settings['CF_dP_ub']
        dPlb = self.__Settings['CF_dP_lb']

        if self.Time[0] == 0:
            self.__PinOld = self.__Pin
        print(self.Time[0], self.__PinOld, self.__Pin)
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:5:2])
        Pbatt = -float(self.__ControlledElm.GetVariable('Powers')[0]) * 3
        ramp = (Pin - self.__PinOld)
        if self.Time[0] > 1:
            if ramp >= dPub:
                dPbatt = self.__dampCoef * (ramp - dPub)
                Pbatt += dPbatt
            elif ramp <= dPlb:
                dPbatt = self.__dampCoef * (ramp - dPlb)
                Pbatt += dPbatt
            else:
                dPbatt = 0
                Pbatt = 0
            if Pbatt > 0:
                pctdischarge = Pbatt / self.__Prated * 100
                self.__ControlledElm.SetParameter('State', 'DISCHARGING')
                self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
            elif Pbatt < 0:
                pctcharge = -Pbatt / self.__Prated * 100
                self.__ControlledElm.SetParameter('State', 'CHARGING')
                self.__ControlledElm.SetParameter('%charge', str(pctcharge))
            elif Pbatt == 0:
                self.__ControlledElm.SetParameter('State', 'IDLING')
            self.__Pin = Pin
        else:
            self.__PinOld = Pin
            self.__Pin = Pin
            return 0

        Error = abs(dPbatt)
        return Error

    def ConstantPowerFactorControl(self):
        PF = self.__Settings['pf']
        self.__dssSolver.reSolve()
        Pcalc = float(self.__ControlledElm.GetParameter2('kw')) / self.__Prated

        if Pcalc > 0:
            Qcalc = float(self.__ControlledElm.GetParameter2('kvar')) / self.__Prated

            Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
            if Scalc > 1:
                Scaler = (1 - (Scalc - 1) / Scalc)
                Pcalc = Pcalc * Scaler
            if Pcalc > 0:
                self.__ControlledElm.SetParameter('%Discharge', Pcalc * 100)
            elif Pcalc < 0:
                self.__ControlledElm.SetParameter('%charge', -Pcalc * 100)

            self.__ControlledElm.SetParameter('pf', str(-PF))
        else:
            self.__ControlledElm.SetParameter('pf', str(1))

        return 0

    def VariablePowerFactorControl(self):
        pMin = self.__Settings['Pmin']
        pMax = self.__Settings['Pmax']
        pfMin = self.__Settings['pfMin']
        pfMax = self.__Settings['pfMax']

        self.__dssSolver.reSolve()
        Pcalc = float(self.__ControlledElm.GetParameter2('kw')) / self.__Prated

        if Pcalc > 0:
            if Pcalc < pMin:
                PF = pfMax
            elif Pcalc > pMax:
                PF = pfMin
            else:
                m = (pfMax - pfMin) / (pMin - pMax)
                c = (pfMin * pMin - pfMax * pMax) / (pMin - pMax)
                PF = Pcalc * m + c
        else:
            PF = pfMax
        print (Pcalc,PF)

        Qcalc =  (Pcalc / PF) * math.sin(math.acos(PF))

        Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
        if Scalc > 1:
            Scaler = (1 - (Scalc - 1) / Scalc)
            Qcalc = Qcalc * Scaler
            PF = math.cos(math.atan(Qcalc/Pcalc))

        self.__ControlledElm.SetParameter('pf', str(-PF))
        if Pcalc > 0:
            self.__ControlledElm.SetParameter('%Discharge', Pcalc*100)
        elif Pcalc < 0:
            self.__ControlledElm.SetParameter('%charge', -Pcalc*100)
        return 0

    def VoltVarControl(self):

        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        QlimPU = self.__Settings['QlimPU']
        PFlim = self.__Settings['PFlim']

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])

        m1 = QlimPU / (uMin-uDbMin)
        m2 = QlimPU / (uDbMax-uMax)
        c1 = QlimPU * uDbMin / (uDbMin-uMin)
        c2 = QlimPU * uDbMax / (uMax-uDbMax)

        Ppv = float(self.__ControlledElm.GetParameter2('kw'))
        Pcalc = Ppv / self.__Srated
        Qpv = sum(self.__ControlledElm.GetVariable('Powers')[1::2])
        Qpv = Qpv / self.__Srated

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

        # adding heavy ball term to improve convergence
        Qcalc = Qpv + (Qcalc - Qpv) * 0.5 / self.__dampCoef + (Qpv - self.oldQcalc) * 0.1 / self.__dampCoef
        Qlim = (1 - Pcalc ** 2) ** 0.5 if abs(Pcalc) < 1 else 0 # note - this is watt priority
        if self.__Settings['Enable PF limit']:
            Qlim = min(Qlim, abs(Pcalc * math.tan(math.acos(PFlim))))
        if abs(Qcalc) > Qlim:
            Qcalc = Qlim if Qcalc > 0 else -Qlim

        dQ = abs(Qcalc - Qpv)
        pct = min((Qcalc**2 + Pcalc**2) ** 0.5 * self.__Srated / self.__Prated * 100, 100)
        pf = math.cos(math.atan(Qcalc / Pcalc)) if Pcalc != 0 else 1
        pf = -pf if Qcalc * Pcalc < 0 else pf
        if Pcalc > 0:
            self.__ControlledElm.SetParameter('pf', pf)
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pct))
        elif Pcalc < 0:
            self.__ControlledElm.SetParameter('pf', pf)
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pct))
        else:
            dQ = 0

        Error = abs(dQ)
        # if Error > 0.1 or math.isnan(Error):
        #     print((self.__Name, uIn, Qcalc, Qpv, self.oldQcalc, dQ, Ppv, Pcalc, pct, pf, self.__ControlledElm.GetVariable('Powers')))
        self.oldQcalc = Qcalc
        return Error

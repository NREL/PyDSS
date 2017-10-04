import matplotlib.pyplot as plt
import math

class StorageController:
    I = 0.9
    def __init__(self, StorageObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.__ElmObjectList = ElmObjectList
        self.P_ControlDict = {
            'None'             : lambda : None,
            'Peak Shaving'     : self.PeakShavingControl,
            'Capacity Firming' : self.CapacityFirmimgControl,
            'Load Following'   : self.LoadFollowingControl,
            'Time Triggered'   : self.TimeTriggeredControl,
            'Real Time'        : self.RealTimeControl,
            'Scheduled'        : self.ScheduledControl,}

        self.Q_ControlDict = {
            'None'                   : lambda : None,
            'Variable Power Factor'  : self.VariablePowerFactorControl,
            'Volt Var Control'       : self.VoltVarControl,}

        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = StorageObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings
        self.__Prated = float(StorageObj.GetParameter2('kWrated'))
        self.P_update = self.P_ControlDict[Settings['Pcontrol']]
        self.Q_update = self.Q_ControlDict[Settings['Qcontrol']]
        self.__Pbatt = float(StorageObj.GetParameter2('kW'))

        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name

        self.PinHist = []
        self.PbattHist = []
        self.SOChist = []
        self.uInHist = []
        self.PFbattHist = []
        self.VarBattHist = []
        self.Fig, self.Axs = plt.subplots(3,2, sharex=True)
        from itertools import chain
        self.Axs = list(chain.from_iterable(self.Axs))
        return

    def Update(self,Time):
        if Time >= 0:
            self.UpdateResults()
            self.P_update()
            self.Q_update()

            if Time == 1439:
                for ax in self.Axs:
                    ax.clear()
                    ax.grid()

                self.Axs[0].plot(self.PbattHist)
                self.Axs[2].plot(self.VarBattHist)
                self.Axs[4].plot(self.PFbattHist)
                self.Axs[1].plot(self.PinHist)
                self.Axs[3].plot(self.SOChist)
                self.Axs[5].plot(self.uInHist)
                self.Fig.subplots_adjust(hspace=0)

        return

    def UpdateResults(self):
        if self.__Settings['Meas from Circuit']:
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -Sin[0]
        else:
            Sin = self.__ElmObjectList[self.__Settings['Measured Element']].GetVariable(self.__Settings['Measured Variable'])
            Pin = sum(Sin[0:5:2])
        busName = self.__ControlledElm.GetParameter2('bus1')
        self.__dssInstance.Circuit.SetActiveBus(busName)
        uIn = max(self.__dssInstance.Bus.puVmagAngle()[0::2])
        SOC = self.__ControlledElm.GetParameter2('%stored')
        PF = abs(float(self.__ControlledElm.GetParameter2('pf')))
        Pbatt = float(self.__ControlledElm.GetParameter2('kw'))
        Qbatt = float(self.__ControlledElm.GetParameter2('kvar'))

        self.PinHist.append(Pin)
        self.PbattHist.append(Pbatt)
        self.SOChist.append(SOC)
        self.uInHist.append(uIn)
        self.PFbattHist.append(PF)
        self.VarBattHist.append(Qbatt)
        return

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
        return

    def PeakShavingControl(self):
        Pub = self.__Settings['PS_ub']
        Plb = self.__Settings['PS_lb']
        IdlingkWPercent = float(self.__ControlledElm.GetParameter2('%IdlingkW'))
        IdlingkW = -IdlingkWPercent/100*self.__Prated
        IdlingkW = 0
        if self.__Settings['Meas from Circuit']:
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -Sin[0]
        else:
            Sin = self.__ElmObjectList[self.__Settings['Measured Element']].GetVariable(self.__Settings['Measured Variable'])
            Pin = sum(Sin[0:5:2])
        Pbatt = float(self.__ControlledElm.GetParameter2('kw'))
        dP = 0
        if Pin > Pub:
            dP = Pin - Pub
            Pbatt = Pbatt + dP
        elif Pin < Plb:
            dP = Pin - Plb
            Pbatt = Pbatt + dP
        else:
            if Pbatt > IdlingkW:
                Pbatt = Pbatt - 0.003 * (self.__Prated)
            else:
                Pbatt = Pbatt + 0.003 * (self.__Prated)

        if Pbatt > IdlingkW:
            pctdischarge = Pbatt/ (self.__Prated)* 100
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
        elif Pbatt < IdlingkW:
            pctcharge = -Pbatt  / (self.__Prated)* 100
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))
        return

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
        return

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
        return

    def CapacityFirmimgControl(self):
        return

    def LoadFollowingControl(self):
        return

    def ReaTimeVarControl(self):
        return

    def VariablePowerFactorControl(self):
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        pfMin = self.__Settings['pfMin']
        pfMax = self.__Settings['pfMax']

        busName = self.__ControlledElm.GetParameter2('bus1')
        self.__dssInstance.Circuit.SetActiveBus(busName)
        uIn = max(self.__dssInstance.Bus.puVmagAngle()[0::2])

        Pcalc = float(self.__ControlledElm.GetParameter2('kw')) / self.__Prated
        Qcalc = float(self.__ControlledElm.GetParameter2('kvar')) / self.__Prated

        Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
        if Scalc > 1:
            Scaler = (1 - (Scalc - 1) / Scalc)
            Pcalc = Pcalc * Scaler

        PF = 0
        if uIn < uMin:
            PF = pfMax
        elif uIn > uMax:
            PF = pfMin
        else:
            m = (pfMax-pfMin)/(uMin-uMax)
            c = (pfMin*uMin - pfMax*uMax)/(uMin-uMax)
            PF = uIn * m + c
        self.__ControlledElm.SetParameter('pf', str(-PF))
        if Pcalc > 0:
            self.__ControlledElm.SetParameter('%Discharge', Pcalc*100)
        elif Pcalc < 0:
            self.__ControlledElm.SetParameter('%charge', -Pcalc*100)
        return

    def VoltVarControl(self):
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        QlimPU = self.__Settings['QlimPU']
        PFlim = self.__Settings['PFlim']

        busName = self.__ControlledElm.GetParameter2('bus1')
        self.__dssInstance.Circuit.SetActiveBus(busName)
        uIn = max(self.__dssInstance.Bus.puVmagAngle()[0::2])

        m1 = QlimPU/(uMin-uDbMin)
        m2 = QlimPU/(uDbMax-uMax)
        c1 = QlimPU*uDbMin/(uDbMin-uMin)
        c2 = QlimPU*uDbMax/(uMax-uDbMax)

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


        Pcalc = float(self.__ControlledElm.GetParameter2('kw')) / self.__Prated
        Qlim = abs((Pcalc / PFlim) * math.sin(math.acos(PFlim)))

        if Qcalc < -Qlim:
            Qcalc = -Qlim
        elif Qcalc > Qlim:
            Qcalc = Qlim

        Scalc = (Pcalc**2 + Qcalc**2)**(0.5)
        if Scalc > 1:
            Scaler = (1 - (Scalc - 1)/Scalc)
            Pcalc = Pcalc * Scaler
            Qcalc = Qcalc * Scaler

        if Pcalc != 0:
            PFout  = math.cos(math.atan(Qcalc/Pcalc))
        else:
            PFout = 1

        if Pcalc > 0:
            self.__ControlledElm.SetParameter('pf', str(-PFout))
            self.__ControlledElm.SetParameter('%Discharge', Pcalc*100)
        elif Pcalc < 0:
            self.__ControlledElm.SetParameter('pf', str(PFout))
            self.__ControlledElm.SetParameter('%charge', -Pcalc*100)
        return

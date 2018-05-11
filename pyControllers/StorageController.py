import numpy as np
import math

class StorageController:

    def __init__(self, StorageObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.Time = 0
        self.__Pin = 0
        self.__PinOld = 0
        self.PbattOld = 0
        self.QcalcOld = 0

        self.__ElmObjectList = ElmObjectList
        self.P_ControlDict = {
            'None' : lambda : 0,
            'PS'   : self.PeakShavingControl,
            'CF'   : self.CapacityFirmimgControl,
            'TT'   : self.TimeTriggeredControl,
            'RT'   : self.RealTimeControl,
            'SH'   : self.ScheduledControl,}

        self.Q_ControlDict = {
            'None' : lambda : 0,
            'CPF'  : self.ConstantPowerFactorControl,
            'VPF'  : self.VariablePowerFactorControl,
            'VVar' : self.VoltVarControl,}

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
        #self.__Convergance = np.zeros((1440,10))

        return

    def Update_Q(self, Time, Iteration):
        if Time >= 1:
            #self.Time = Time
            #elf.doUpdate = UpdateResults
            dQ = self.Q_update()
        else:
            dQ = 0
        return dQ

    def Update_P(self, Time, Iteration):
        self.Itr = Iteration
        if Time >= 1:
            self.Time = Time
            dP = self.P_update()
            # self.__Convergance[Time, Iteration] = dP
        else:
            dP = 0

        # if Time == 1439:
        #     np.savetxt(r'C:\Users\alatif\Desktop\PyDSS\Export\Sumitomo-Validation\ESS-CF\Convergance.csv',
        #                self.__Convergance.transpose(), delimiter=',')
        return dP

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
            Pbatt = Pbatt + dP * self.__Settings['DampCoef']
        elif Pin < Plb:
            dP = Pin - Plb
            Pbatt = Pbatt + dP * self.__Settings['DampCoef']
        else:
            Pbatt = 0

        if Pbatt >= 0:
            pctdischarge = Pbatt/ (self.__Prated)* 100
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))

        elif Pbatt < 0:
            pctcharge = -Pbatt   / (self.__Prated)* 100
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))

        Error = abs(Pbatt - self.PbattOld)
        self.PbattOld = Pbatt
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

        if self.Itr == 0:
            self.__PinOld = self.__Pin
        print(self.Itr, self.__PinOld, self.__Pin)
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:5:2])
        Pbatt = -float(self.__ControlledElm.GetVariable('Powers')[0]) * 3
        ramp = (Pin - self.__PinOld)
        if self.Time > 1:
            if ramp >= dPub:
                dPbatt = self.__Settings['DampCoef'] * (ramp - dPub)
                Pbatt += dPbatt
            elif ramp <= dPlb:
                dPbatt = self.__Settings['DampCoef'] * (ramp - dPlb)
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
        busName = self.__ControlledElm.GetParameter2('bus1')

        for i in range(3):
            self.__dssInstance.Circuit.SetActiveBus(busName)
            #uIn = max(self.__dssInstance.Bus.puVmagAngle()[0::2])
            uIn = self.__dssInstance.Bus.puVmagAngle()[0]

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
            # Qlim = abs((Pcalc / PFlim) * math.sin(math.acos(PFlim)))
            #
            # if Qcalc < -Qlim:
            #     Qcalc = -Qlim
            # elif Qcalc > Qlim:
            #     Qcalc = Qlim
            # #
            # Scalc = (Pcalc**2 + Qcalc**2)**(0.5)
            # if Scalc > 1:
            #     Scaler = (1 - (Scalc - 1)/Scalc)
            #     Pcalc = Pcalc * Scaler
            #     Qcalc = Qcalc * Scaler


            if Pcalc > 0:
                PFout = math.cos(math.atan(Qcalc / Pcalc))
                self.__ControlledElm.SetParameter('pf', str(-PFout))
                #self.__ControlledElm.SetParameter('%Discharge', Pcalc*100)
            elif Pcalc <= 0:
                PFout = 1
                self.__ControlledElm.SetParameter('pf', str(PFout))
                #self.__ControlledElm.SetParameter('%charge', -Pcalc*100)
            self.__dssSolver.reSolve()
            Error = (Qcalc - self.QcalcOld)**2
            self.QcalcOld = Qcalc
        return Error

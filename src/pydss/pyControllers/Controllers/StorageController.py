from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract
import calendar
import math
import ast

class StorageController(ControllerAbstract):
    """Numerous control implementation for a storage system from both behind-the-meter and front-of- meter applications. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

            :param StorageObj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS Storage element
            :type FaultObj: class:`pydss.dssElement.dssElement`
            :param Settings: A dictionary that defines the settings for the PvController.
            :type Settings: dict
            :param dssInstance: An :class:`opendssdirect` instance
            :type dssInstance: :class:`opendssdirect`
            :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
            :type ElmObjectList: dict
            :param dssSolver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
            :type dssSolver: :mod:`pydss.SolveMode`
            :raises: AssertionError if 'StorageObj' is not a wrapped OpenDSS Storage element

    """
    def __init__(self, StorageObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.Time = -1
        super(StorageController, self).__init__(StorageObj, Settings, dssInstance, ElmObjectList, dssSolver)

        self.__ControlledElm = StorageObj
        self.ceClass, self.ceName = self.__ControlledElm.GetInfo()
        assert (self.ceClass.lower() == 'storage'), 'StorageController works only with an OpenDSS Storage element'
        self.__Name = 'pyCont_' + self.ceClass + '_' + self.ceName

        self.Time = (-1, 0)
        self.__Pin = 0
        self.Pbatt = 0
        self.__PinOld = 0
        self.PbattOld = 0
        self.oldQcalc = 0
        self.ExportOld = False
        self.__ElmObjectList = ElmObjectList

        self.ControlDict = {
            'None'   : lambda: 0,
            'PS'     : self.PeakShavingControl,
            'CF'     : self.CapacityFirmimgControl,
            'TT'     : self.TimeTriggeredControl,
            'RT'     : self.RealTimeControl,
            'SH'     : self.ScheduledControl,
            'NETT'   : self.NonExportTimeTriggered,
            'TOU'    : self.TimeOfUse,
            'DemChg' : self.DemandCharge,
            'CPF'    : self.ConstantPowerFactorControl,
            'VPF'    : self.VariablePowerFactorControl,
            'VVar'   : self.VoltVarControl,
        }

        self.__a = Settings['alpha']
        self.__b = Settings['beta']
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = StorageObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.__Srated = float(StorageObj.GetParameter('kVA'))
        self.__Prated = float(StorageObj.GetParameter('kWrated'))
        self.__Pbatt = float(StorageObj.GetParameter('kW'))
        self.__dampCoef = Settings['DampCoef']
        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]
        return

    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.ceClass, self.ceName)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]

    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Time, Priority)
        self.Time = (Time, Priority)
        return self.update[Priority]()

    def SetSetting(self, Property, Value):
        self.__Settings[Property] = Value
        return

    def GetSetting(self, Property):
        return self.__Settings[Property]

    def __parseRatePlan(self, tarrif):
        self.touTarrif = ast.literal_eval(tarrif)
        CurrDateTime = self.__dssSolver.GetDateTime()
        DayOfYear = CurrDateTime.timetuple().tm_yday
        weekno = CurrDateTime.weekday()
        currentDay = calendar.day_name[weekno]

        for period, touDetails in self.touTarrif.items():
            if touDetails['ED'] < touDetails['SD']:
                TOUday = [i for j in (range(1, touDetails['ED']), range(touDetails['SD'], 365)) for i in j]
            else:
                TOUday = range(touDetails['SD'], touDetails['ED'] + 1)
            if DayOfYear in TOUday:
                if currentDay in touDetails['TOW']:
                    for st, et in zip(touDetails['ST'], touDetails['ET']):
                        if et < st:
                            TOUtime = [i for j in (range(1, et), range(st, 25)) for i in j]
                        else:
                            TOUtime = range(st, et)
                        if CurrDateTime.hour in TOUtime:
                            return True
                else:
                    pass
        return False

    def TimeOfUse(self):
        """ Implementation of a time of use controller for behind the meter applications
        """
        dP = 0
        Pub = self.__Settings['touLoadLim']
        touCharge = self.__Settings['%touCharge']
        tarrif = self.__Settings['touTarrifStructure']
        isTOU = self.__parseRatePlan(tarrif)
        Pbatt = float(self.__ControlledElm.GetParameter('kw'))
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:5:2])

        if isTOU:
            if Pin > Pub:
                dP = Pin - Pub
                Pbatt = Pbatt + dP * self.__a - (Pbatt - self.PbattOld) * self.__b
            else:
                Pbatt = 0
        else:
            Pbatt =  -touCharge * self.__Prated / 100

        if Pbatt >= 0:
            pctdischarge = Pbatt / (self.__Prated) * 100
            pctdischarge = 100 if pctdischarge > 100 else pctdischarge
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
        if Pbatt < 0:
            pctcharge = -Pbatt / (self.__Prated) * 100
            pctcharge = 100 if pctcharge > 100 else pctcharge
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))

        Error = abs(Pbatt - self.PbattOld)
        self.PbattOld = Pbatt
        self.dPold = dP
        return Error


    def DemandCharge(self):
        """ Implementation of a demand charge controller for behind the meter applications
        """

        self.Demand = 0
        dP = 0
        DemandChgThreh = self.__Settings['DemandChgThreh[kWh]']
        Pub = self.__Settings['touLoadLim']
        touCharge = self.__Settings['%touCharge']
        tarrif = self.__Settings['touTarrifStructure']
        isTOU = self.__parseRatePlan(tarrif)
        Pbatt = float(self.__ControlledElm.GetParameter('kw'))
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:5:2])
        DateAndTime = self.__dssSolver.GetDateTime()
        CurrMin = DateAndTime.minute
        if isTOU:
            i = CurrMin % 30
            if i == 0:
                self.__EnergyCounter = [0 for i in range(30)]
            self.__EnergyCounter[i] = Pin
            self.Demand = sum(self.__EnergyCounter) / (60 / self.__dssSolver.GetStepResolutionMinutes())

            if self.Demand >= 0.9 * DemandChgThreh:
                if Pin > Pub:
                    dP = Pin - Pub
                    Pbatt = Pbatt + (dP) * self.__a - (Pbatt - self.PbattOld) * self.__b
                else:
                    Pbatt = 0
            else:
                Pbatt = 0
        else:
            Pbatt = -touCharge * self.__Prated / 100

        if Pbatt >= 0:
            pctdischarge = Pbatt / (self.__Prated) * 100
            pctdischarge =  100 if  pctdischarge > 100 else pctdischarge
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
        if Pbatt < 0:
            pctcharge = -Pbatt / (self.__Prated) * 100
            pctcharge = 100 if pctcharge > 100 else pctcharge
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))

        Error = abs(Pbatt - self.PbattOld)
        self.PbattOld = Pbatt
        self.dPold = dP
        return Error

    def ScheduledControl(self):
        """ Implementation of a fixed schedule controller. Used to implemented predefined dispatch signals
        """
        P_profile = self.__Settings['Schedule']
        Days = self.__Settings['Days']
        LenSchedule = len(P_profile)
        TotalSeconds = 24*60*60*Days
        TimeStepPerSample = int(TotalSeconds / LenSchedule)

        CurrentTime = int(self.__dssInstance.Solution.Hour()) * 60 * 60 + \
                      int(self.__dssInstance.Solution.Seconds())

        Index = int(CurrentTime / TimeStepPerSample)
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
        """ Implementation of a smart non-export controller. Makes use of TOU window to optimize charging
        """
        # self.dPold = 0
        dP = 0
        Plb = self.__Settings['BaseLoadLim']
        sTime = self.__Settings['ExpWindowStart']
        eTime = self.__Settings['ExpWindowEnd']
        KWHrated = float(self.__ControlledElm.GetParameter('kWhrated'))
        perIdle = float(self.__ControlledElm.GetParameter('%IdlingkW'))
        effDchg = float(self.__ControlledElm.GetParameter('%EffDischarge'))

        Minutes = int(self.__dssInstance.Solution.Seconds() / 60)
        Hour = self.__dssInstance.Solution.Hour() % 24

        if sTime.hour < eTime.hour:
            Twindow = ((eTime.hour * 60 + eTime.minute) - (sTime.hour * 60 + sTime.minute)) / 60
            if (Hour * 60 + Minutes) > (sTime.hour * 60 + sTime.minute) and (Hour * 60 + Minutes) < (eTime.hour * 60 + eTime.minute):
                Export = True
            else:
                Export = False
        else:
            Twindow = 24 - ((sTime.hour * 60 + sTime.minute) - (eTime.hour * 60 + eTime.minute)) / 60
            if (Hour * 60 + Minutes) > (sTime.hour * 60 + sTime.minute) or \
                    (Hour * 60 + Minutes) < (eTime.hour * 60 + eTime.minute):
                Export = True
            else:
                Export = False

        if self.ExportOld == False and Export == True:
            perKWHstored = float(self.__ControlledElm.GetParameter('%stored'))
            kWhrem = KWHrated * (perKWHstored / 100)
            self.Pbatt = kWhrem / (Twindow) * effDchg / 100 - perIdle * self.__Prated / 100
        self.ExportOld = Export

        if Export:
            pctcharge = self.Pbatt / (self.__Prated) * 100
            rT = ((eTime.hour * 60 + eTime.minute) - (Hour * 60 + Minutes)) / 60
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctcharge))
            Error = 0
        else:
            if self.__Settings['PowerMeaElem'] == 'Total':
                Sin = self.__dssInstance.Circuit.TotalPower()
                Pin = -sum(Sin[0:5:2])
            else:
                Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
                Sin2 = Sin[:int(len(Sin) / 2)]
                Pin = sum(Sin2[0::2])
            Pbatt = float(self.__ControlledElm.GetParameter('kw'))
            if Pin < Plb:
                dP = Plb - Pin
                Pbatt = Pbatt - (dP) * self.__a - (Pbatt - self.PbattOld) * self.__b
            else:
                Pbatt = 0

            if Pbatt >= 0:
                pctdischarge = Pbatt / (self.__Prated) * 100
                self.__ControlledElm.SetParameter('State', 'DISCHARGING')
                self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))
            if Pbatt < 0:
                pctcharge = -Pbatt / (self.__Prated) * 100
                self.__ControlledElm.SetParameter('State', 'CHARGING')
                self.__ControlledElm.SetParameter('%charge', str(pctcharge))

            Error = abs(Pbatt - self.PbattOld)
            self.PbattOld = Pbatt
            self.dPold = dP
        return Error

    def PeakShavingControl(self):
        """ Implementation of a peak shaving / base loading controller. Setting both peak shaving and base loading
        limits to zero will make the storage work in "SELF CONSUMPTION" mode
        """
        Pub = self.__Settings['PS_ub']
        Plb = self.__Settings['PS_lb']
        IdlingkWPercent = float(self.__ControlledElm.GetParameter('%IdlingkW'))
        IdlingkW = -IdlingkWPercent/100*self.__Prated
        if self.__Settings['PowerMeaElem'] == 'Total':
            Sin = self.__dssInstance.Circuit.TotalPower()
            Pin = -sum(Sin[0:5:2])
        else:
            Sin = self.__ElmObjectList[self.__Settings['PowerMeaElem']].GetVariable('Powers')
            Pin = sum(Sin[0:int(len(Sin)/2):2])

        Pbatt = float(self.__ControlledElm.GetParameter('kw'))

        if Pin > Pub:
            dP = Pin - Pub
            Pbatt = Pbatt + dP * self.__dampCoef
        elif Pin < Plb:
            dP = Pin - Plb
            Pbatt = Pbatt + dP * self.__dampCoef
        else:
            Pbatt = Pbatt * self.__dampCoef

        if Pbatt >= 0:
            pctdischarge = min(100, Pbatt / self.__Prated* 100)
            pctdischarge = 100 if pctdischarge > 100 else pctdischarge
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(pctdischarge))

        elif Pbatt < 0:
            pctcharge = min(100, -Pbatt / (self.__Prated)* 100)
            pctcharge = 100 if pctcharge > 100 else pctcharge
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(pctcharge))

        Error = abs(Pbatt - self.PbattOld) / self.__Srated
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
        Hour = self.__dssInstance.Solution.Hour() % 24
        if Hour == HrC and Minutes == MnC:
            self.__ControlledElm.SetParameter('State', 'CHARGING')
            self.__ControlledElm.SetParameter('%charge', str(rateCharge))
        elif Hour == HrD and Minutes == MnD:
            self.__ControlledElm.SetParameter('State', 'DISCHARGING')
            self.__ControlledElm.SetParameter('%Discharge', str(rateDischarge))
        return 0

    def CapacityFirmimgControl(self):
        """ Implementation of a capacity firming algorithm
        """
        dPub = self.__Settings['CF_dP_ub']
        dPlb = self.__Settings['CF_dP_lb']

        if self.Time[0] == 0:
            self.__PinOld = self.__Pin

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
        """ Implementation of a constant power factor algorithm. In all cases of reactive power support, active power
        will be prioritized over reactive power.
        """
        PF = self.__Settings['pf']
        self.__dssSolver.reSolve()
        Pcalc = float(self.__ControlledElm.GetParameter('kw')) / self.__Prated

        if Pcalc > 0:
            Qcalc = float(self.__ControlledElm.GetParameter('kvar')) / self.__Prated

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
        """ Implementation of a variable power factor algorithm. In all cases of reactive power support, active power
            will be prioritized over reactive power.
        """

        pMin = self.__Settings['Pmin']
        pMax = self.__Settings['Pmax']
        pfMin = self.__Settings['pfMin']
        pfMax = self.__Settings['pfMax']

        self.__dssSolver.reSolve()
        Pcalc = float(self.__ControlledElm.GetParameter('kw')) / self.__Prated

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
        """ Implementation of a Volt / var algorithm. Enables the storage to stack multiple services. In all cases of
        reactive power support, active power will be prioritized over reactive power.
        """
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

        Ppv = float(self.__ControlledElm.GetParameter('kw'))
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
        self.oldQcalc = Qcalc
        return Error

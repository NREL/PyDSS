from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
from shapely.geometry import MultiPoint, Polygon, Point, MultiPolygon
from shapely.ops import triangulate, cascaded_union
from descartes.patch import PolygonPatch
import datetime
import math
import os

class PvVoltageRideThru(ControllerAbstract):
    """Implementation of IEEE1547-2003 and IEEE1547-2018 voltage ride-through standards using the OpenDSS Generator model. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

            :param PvObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Generator' element
            :type FaultObj: class:`PyDSS.dssElement.dssElement`
            :param Settings: A dictionary that defines the settings for the PvController.
            :type Settings: dict
            :param dssInstance: An :class:`opendssdirect` instance
            :type dssInstance: :class:`opendssdirect`
            :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
            :type ElmObjectList: dict
            :param dssSolver: An instance of one of the classed defined in :mod:`PyDSS.SolveMode`.
            :type dssSolver: :mod:`PyDSS.SolveMode`
            :raises: AssertionError if 'PvObj' is not a wrapped OpenDSS Generator element

    """

    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(PvVoltageRideThru).__init__( PvObj, Settings, dssInstance, ElmObjectList, dssSolver)

        self.TimeChange = False
        self.Time = (-1, 0)

        self.oldPcalc = 0
        self.oldQcalc = 0
        self.Qpvpu = 0
        self. __vDisconnected = False
        self.__pDisconnected = False

        self.__ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None'           : lambda: 0,
            'CPF'            : self.CPFcontrol,
            'VPF'            : self.VPFcontrol,
            'VVar'           : self.VVARcontrol,
            'VW'             : self.VWcontrol,
            #'Cutoff'         : self.CutoffControl,
        }

        self.__ControlledElm = PvObj
        self.__ElmObjectList = ElmObjectList
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        Class, Name = self.__ControlledElm.GetInfo()
        assert (Class.lower() == 'generator'), 'PvControllerGen works only with an OpenDSS Generator element'
        self.__Name = 'pyCont_' + Class + '_' + Name
        if '_' in Name:
            self.Phase = Name.split('_')[1]
        else:
            self.Phase = None

        # Initializing the model
        PvObj.SetParameter('kvar', 0)
        #self.__BaseKV = float(PvObj.SetParameter('kv',Settings['kV']))
        self.__Srated = float(PvObj.SetParameter('kva',Settings['kVA']))
        self.__Prated = float(PvObj.SetParameter('kW',Settings['maxKW']))
        self.__minQ = float(PvObj.SetParameter('minkvar',-Settings['KvarLimit']))
        self.__maxQ = float(PvObj.SetParameter('maxkvar',Settings['KvarLimit']))

        # MISC settings
        self.__cutin = Settings['%PCutin']
        self.__cutout = Settings['%PCutout']
        self.__trip_deadtime_sec = Settings['Reconnect deadtime - sec']
        self.__Time_to_Pmax_sec = Settings['Reconnect Pmax time - sec']
        self.__alpha = Settings['alpha']
        self.__beta = Settings['beta']
        self.__Prated = Settings['maxKW']
        self.__priority = Settings['Priority']
        self.__enablePFlimit = Settings['Enable PF limit']
        self.__minPF = Settings['pfMin']
        self.__UcalcMode = Settings['UcalcMode']
        #self.__VVtConst = Settings['VVtConst']
        #self.__VWtConst = Settings['VWtConst']
        # Settings for voltvar
        self.__uMin = self.__Settings['uMin']
        self.__uMax = self.__Settings['uMax']
        self.__uDbMin = self.__Settings['uDbMin']
        self.__uDbMax = self.__Settings['uDbMax']
        # Settings for voltwatt
        self.__uMinC = self.__Settings['uMinC']
        self.__uMaxC = self.__Settings['uMaxC']
        self.__Pmin = self.__Settings['PminVW'] / 100
        self.__curtailmentMode = self.__Settings['CurtMode']
        # Update function calls
        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]
        # initialize deadtimes and other variables
        self.__initializeRideThroughSettings()
        self.__rVs, self.__rTs = self.__CreateOperationRegions()
        # For debugging only
        # self.voltage = list(range(96))
        # self.reactive_power = list(range(96))
        # self.reactive_power_2 = list(range(96))

        self.__VoltVioM = False
        self.__VoltVioP = False
        return

    def __initializeRideThroughSettings(self):
        self.__isConnected = True
        self.__Plimit = self.__Prated
        self.__CutoffTime = self.__dssSolver.GetDateTime()
        self.__ReconnStartTime = self.__dssSolver.GetDateTime() - datetime.timedelta(
            seconds=int(self.__Time_to_Pmax_sec))

        self.__TrippedPmaxDelay = 0
        self.__NormOper = True
        self.__NormOperStartTime = self.__dssSolver.GetDateTime()
        self.__uViolationtime = 999999
        self.__TrippedStartTime = self.__dssSolver.GetDateTime()
        self.__TrippedDeadtime = 0
        self.__faultCounter = 0
        self.__isinContioeousRegion = True
        self.__FaultwindowClearingStartTime = self.__dssSolver.GetDateTime()

        return

    def __CreateOperationRegions(self):
        uMaxTheo = 10
        tMax = 1e10

        OVtripPoints = [
            Point(uMaxTheo, self.__Settings['OV2 CT - sec']),
            Point(self.__Settings['OV2 - p.u.'], self.__Settings['OV2 CT - sec']),
            Point(self.__Settings['OV2 - p.u.'], self.__Settings['OV1 CT - sec']),
            Point(self.__Settings['OV1 - p.u.'], self.__Settings['OV1 CT - sec']),
            Point(self.__Settings['OV1 - p.u.'], tMax),
            Point(uMaxTheo, tMax)
        ]
        OVtripRegion = Polygon([[p.y, p.x] for p in OVtripPoints])

        UVtripPoints = [
            Point(0, self.__Settings['UV2 CT - sec']),
            Point(self.__Settings['UV2 - p.u.'], self.__Settings['UV2 CT - sec']),
            Point(self.__Settings['UV2 - p.u.'], self.__Settings['UV1 CT - sec']),
            Point(self.__Settings['UV1 - p.u.'], self.__Settings['UV1 CT - sec']),
            Point(self.__Settings['UV1 - p.u.'], tMax),
            Point(0, tMax)
        ]
        UVtripRegion = Polygon([[p.y, p.x] for p in UVtripPoints])

        if self.__Settings['Ride-through Category'] == 'Category I':
            V = [1.10, 0.88, 0.7, 1.20, 1.175, 1.15, 0.5, 0.5]
            T = [1.5, 0.7, 0.2, 0.5, 1, 0.16, 0.16]
            self.__faultCounterMax = 2
            self.__faultCounterClearingTimeSec = 20

        elif self.__Settings['Ride-through Category'] == 'Category II':
            V = [1.10, 0.88, 0.65, 1.20, 1.175, 1.15, 0.45, 0.30]
            T = [5, 3, 0.2, 0.5, 1, 0.32, 0.16]
            self.__faultCounterMax = 2
            self.__faultCounterClearingTimeSec = 10

        elif self.__Settings['Ride-through Category'] == 'Category III':
            V = [1.10, 0.88, 0.5, 1.2, 1.2, 1.2, 0.0, 0.0]
            T = [21, 10, 13, 13, 13, 1, 1]
            self.__faultCounterMax = 3
            self.__faultCounterClearingTimeSec = 5

        self.__ControlledElm.SetParameter('Model', '7')
        self.__ControlledElm.SetParameter('Vmaxpu', V[0])
        self.__ControlledElm.SetParameter('Vminpu', V[1])

        ContineousPoints = [Point(V[0], 0), Point(V[0], tMax), Point(V[1], tMax), Point(V[1], 0)]
        ContineousRegion = Polygon([[p.y, p.x] for p in ContineousPoints])

        MandatoryPoints = [Point(V[1], 0), Point(V[1], T[0]), Point(V[2], T[1]), Point(V[2], 0)]
        MandatoryRegion = Polygon([[p.y, p.x] for p in MandatoryPoints])

        PermissiveOVPoints = [Point(V[3], 0), Point(V[3], T[2]), Point(V[4], T[2]), Point(V[4], T[3]),
                              Point(V[5], T[3]),
                              Point(V[5], T[4]), Point(V[0], T[4]), Point(V[0], 0.0)]
        PermissiveOVRegion = Polygon([[p.y, p.x] for p in PermissiveOVPoints])

        PermissiveUVPoints = [Point(V[2], 0), Point(V[2], T[5]), Point(V[6], T[5]), Point(V[6], T[6]),
                              Point(V[7], T[6]), Point(V[7], 0)]
        PermissiveUVRegion = Polygon([[p.y, p.x] for p in PermissiveUVPoints])

        ActiveRegion = MultiPolygon([OVtripRegion, UVtripRegion, ContineousRegion, MandatoryRegion,
                                     PermissiveOVRegion, PermissiveUVRegion])

        TotalPoints = [Point(uMaxTheo, 0), Point(uMaxTheo, tMax), Point(0, tMax), Point(0, 0)]
        TotalRegion = Polygon([[p.y, p.x] for p in TotalPoints])
        intersection = TotalRegion.intersection(ActiveRegion)
        MayTripRegion = TotalRegion.difference(intersection)

        if self.__Settings['Ride-through Category'] in ['Category I', 'Category II']:
            if self.__Settings['Permissive operation'] == 'Current limited':
                if self.__Settings['May trip operation'] == 'Permissive operation':
                    self.CurrLimRegion = cascaded_union(
                        [PermissiveOVRegion, PermissiveUVRegion, MandatoryRegion, MayTripRegion])
                    self.MomentarySucessionRegion = None
                    self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion])
                else:
                    self.CurrLimRegion = cascaded_union([PermissiveOVRegion, PermissiveUVRegion, MandatoryRegion])
                    self.MomentarySucessionRegion = None
                    self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion, MayTripRegion])
            else:
                if self.__Settings['May trip operation'] == 'Permissive operation':
                    self.CurrLimRegion = MandatoryRegion
                    self.MomentarySucessionRegion = cascaded_union([PermissiveOVRegion, PermissiveUVRegion, MayTripRegion])
                    self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion])
                else:
                    self.CurrLimRegion = MandatoryRegion
                    self.MomentarySucessionRegion = cascaded_union([PermissiveOVRegion, PermissiveUVRegion])
                    self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion, MayTripRegion])
        else:
            if self.__Settings['May trip operation'] == 'Permissive operation':
                self.CurrLimRegion = MandatoryRegion
                self.MomentarySucessionRegion = cascaded_union([PermissiveOVRegion, PermissiveUVRegion, MayTripRegion])
                self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion])
            else:
                self.CurrLimRegion = MandatoryRegion
                self.MomentarySucessionRegion = cascaded_union([PermissiveOVRegion, PermissiveUVRegion])
                self.TripRegion = cascaded_union([OVtripRegion, UVtripRegion, MayTripRegion])
        self.NormalRegion = ContineousRegion
        return V, T

    def Update(self, Priority, Time, Update):

        Error = 0
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = Time
        if Priority == 0:
            self.__isConnected = self.__Connect()
        # if self.__isConnected:
        #     Error = self.update[Priority]()
        if Priority == 2:
            uIn = self.__UpdateViolatonTimers()
            self.VoltageRideThrough(uIn)

        return Error

    def Trip(self, uIn):
        """ Implementation of the IEEE1587-2003 voltage ride-through requirements for inverter systems
        """
        return

    def VoltageRideThrough(self, uIn):
        """ Implementation of the IEEE1587-2018 voltage ride-through requirements for inverter systems
        """
        self.__faultCounterClearingTimeSec = 1

        Pm = Point(self.__uViolationtime, uIn)
        if Pm.within(self.CurrLimRegion):
            isinContioeousRegion = False
            #print('Operating in current limited region.')
        elif self.MomentarySucessionRegion and Pm.within(self.MomentarySucessionRegion):
            #print('Operating in momentary sucession region.')
            isinContioeousRegion = False
            self.__Trip(self.__dssSolver.GetStepSizeSec(), 0.4, False)
        elif Pm.within(self.TripRegion):
            #print('Operating in trip region.')
            isinContioeousRegion = False
            self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False)
        else:
            isinContioeousRegion = True

        if isinContioeousRegion and not self.__isinContioeousRegion:
            self.__FaultwindowClearingStartTime = self.__dssSolver.GetDateTime()
        clearingTime = (self.__dssSolver.GetDateTime() - self.__FaultwindowClearingStartTime).total_seconds()


        if self.__isinContioeousRegion and not isinContioeousRegion:
            if  clearingTime <= self.__faultCounterClearingTimeSec:
                self.__faultCounter += 1
                if self.__faultCounter >= self.__faultCounterMax:
                    if self.__Settings['Multiple disturbances'] == 'Trip':
                        print('Forced tripping')
                        self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, True)
                        self.__faultCounter = 0
                    else:
                        pass
        if  clearingTime > self.__faultCounterClearingTimeSec and self.__faultCounter > 0:
            self.__faultCounter = 0
        self.__isinContioeousRegion = isinContioeousRegion
        return

    def __Connect(self):
        if not self.__isConnected:
            uIn = self.__ControlledElm.GetVariable('VoltagesMagAng')[::2]
            uBase = self.__ControlledElm.sBus[0].GetVariable('kVBase') * 1000
            uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
            deadtime  =  (self.__dssSolver.GetDateTime() - self.__TrippedStartTime).total_seconds()
            if uIn < self.__rVs[0] and uIn > self.__rVs[1] and deadtime >= self.__TrippedDeadtime:
                self.__ControlledElm.SetParameter('enabled', True)
                self.__isConnected = True
                self.__ControlledElm.SetParameter('kw', 0)
                self.__ReconnStartTime = self.__dssSolver.GetDateTime()
        else:
            conntime = (self.__dssSolver.GetDateTime() - self.__ReconnStartTime).total_seconds()
            self.__Plimit = conntime / self.__TrippedPmaxDelay * self.__Prated if conntime < self.__TrippedPmaxDelay \
                else self.__Prated
            self.__ControlledElm.SetParameter('kw', self.__Plimit)
        return self.__isConnected

    def __Trip(self, Deadtime, Time2Pmax, forceTrip):
        if self.__isConnected or forceTrip:
            self.__ControlledElm.SetParameter('enabled', False)
            self.__isConnected = False
            self.__TrippedStartTime = self.__dssSolver.GetDateTime()
            self.__TrippedPmaxDelay = Time2Pmax
            self.__TrippedDeadtime = Deadtime
        return

    def __UpdateViolatonTimers(self):
        uIn = self.__ControlledElm.GetVariable('VoltagesMagAng')[::2]
        uBase = self.__ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
        if uIn < self.__rVs[0] and uIn > self.__rVs[1]:
            if not self.__NormOper:
                self.__NormOper = True
                self.__NormOperStartTime = self.__dssSolver.GetDateTime()
                self.__NormOperTime = 0
            else:
                self.__NormOperTime = (self.__dssSolver.GetDateTime() - self.__NormOperStartTime).total_seconds()
            self.__VoltVioM = False
            self.__VoltVioP = False
        else:
            if not self.__VoltVioM:
                self.__VoltVioM = True
                self.__uViolationstartTime = self.__dssSolver.GetDateTime()
                self.__uViolationtime = 0
            else:
                self.__uViolationtime = (self.__dssSolver.GetDateTime() - self.__uViolationstartTime).total_seconds()
        return uIn

    def VVARcontrol(self):
        if self.TimeChange:
            self.__ControlledElm.SetParameter('kw', self.__Prated)

        # Read measured variables
        uIn = self.__ControlledElm.GetVariable('VoltagesMagAng')[::2]
        uBase = self.__ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        uIn = max(uIn)/uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
        Ppv = sum(self.__ControlledElm.GetVariable('Powers')[::2])
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2])
        # calculate per unit values

        QlimPU = self.__maxQ / self.__Srated
        Ppvpu = Ppv / self.__Srated
        Qpvpu = Qpv / self.__Srated

        # calculate equation parameters for the VVAR droop curve
        m1 = QlimPU / (self.__uMin - self.__uDbMin)
        m2 = QlimPU / (self.__uDbMax - self.__uMax)
        c1 = QlimPU * self.__uDbMin / (self.__uDbMin - self.__uMin)
        c2 = QlimPU * self.__uDbMax / (self.__uMax - self.__uDbMax)

        # Droop curve used to calculate reactive power set point for the inverter
        Qcalc = 0
        if uIn <= self.__uMin:
            Qcalc = QlimPU
        elif uIn <= self.__uDbMin and uIn > self.__uMin:
            Qcalc = uIn * m1 + c1
        elif uIn <= self.__uDbMax and uIn > self.__uDbMin:
            Qcalc = 0
        elif uIn <= self.__uMax and uIn > self.__uDbMax:
            Qcalc = uIn * m2 + c2
        elif uIn >= self.__uMax:
            Qcalc = -QlimPU

        # Adding heavy ball term to improve convergence
        dQ = Qcalc - Qpvpu
        QpvNew = Qpvpu + dQ * self.__alpha  + (Qpvpu - self.Qpvpu) * self.__beta
        QpvNew = min([max([QpvNew, -QlimPU]), QlimPU])
        self.Qpvpu = Qpvpu

        # Calculate the active power limit (dependent on the chosen priority)
        if self.__priority == 'Var':
            Pscaler = (1 - QpvNew ** 2) ** 0.5
            print(QpvNew, self.__Srated * Qcalc, Qcalc)
            P = self.__Srated * Pscaler
            Q = self.__Srated * QpvNew
            pfCalc = math.cos(math.atan(QpvNew / Pscaler))
        elif self.__priority == 'Watt':
            Qscaler = abs((1 - min([Ppvpu, 1]) ** 2) ** 0.5)
            P = self.__Prated
            Q = self.__Srated * min([max([QpvNew, -Qscaler]), Qscaler])
            pfCalc = math.cos(math.atan(QpvNew / 1))
        elif self.__priority == 'Equal':
            Pmax = self.__Prated / self.__Srated
            scaler = (Ppvpu ** 2 + QpvNew ** 2) ** 0.5
            if scaler > 1:
                Pscaler = Pmax / scaler
                Qscaler = Qcalc / scaler
                P = self.__Srated * Pscaler
                Q = self.__Srated * Qscaler
                pfCalc = math.cos(math.atan(Pscaler / Qscaler))
            else:
                P = self.__Prated
                Q = self.__Srated * QpvNew

                pfCalc = math.cos(math.atan(QpvNew))
        else:
            pass

        self.__ControlledElm.SetParameter('kw', P)
        self.__ControlledElm.SetParameter('kvar', Q)

        # Check for PF violation
        if self.__enablePFlimit:
            if pfCalc < self.__minPF:
                if uIn > 1:
                    self.__ControlledElm.SetParameter('pf', -self.__minPF)
                else:
                    self.__ControlledElm.SetParameter('pf', self.__minPF)
        # Calculate convergence error
        Error = abs(self.oldQcalc - Qpv)
        self.oldQcalc = Qpv
        return Error

    def VWcontrol(self):
        # Get measurement values for the volt var controller
        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])
        Ppv = -sum(self.__ControlledElm.GetVariable('Powers')[::2]) / self.__Srated
        Qpv = -sum(self.__ControlledElm.GetVariable('Powers')[1::2]) / self.__Srated

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

    def CPFcontrol(self):
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


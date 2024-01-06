from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
from shapely.geometry import MultiPoint, Polygon, Point, MultiPolygon
from shapely.ops import triangulate, unary_union
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
        super(PvVoltageRideThru, self).__init__(PvObj, Settings, dssInstance, ElmObjectList, dssSolver)

        self.TimeChange = False
        self.Time = (-1, 0)

        self.oldPcalc = 0
        self.oldQcalc = 0
        self.Qpvpu = 0
        self. __vDisconnected = False
        self.__pDisconnected = False

        self.__ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None': lambda: 0,
        }

        self._ControlledElm = PvObj
        self.__ElmObjectList = ElmObjectList
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.Class, self.Name = self._ControlledElm.GetInfo()
        assert (self.Class.lower() == 'generator'), 'PvControllerGen works only with an OpenDSS Generator element'
        self.__Name = 'pyCont_' + self.Class + '_' + self.Name
        if '_' in self.Name:
            self.Phase = self.Name.split('_')[1]
        else:
            self.Phase = None

        # Initializing the model
        PvObj.SetParameter('kvar', 0)
        self.__Srated = float(PvObj.SetParameter('kva', Settings['kVA']))
        self.__Prated = float(PvObj.SetParameter('kW', Settings['maxKW']))
        self.__minQ = float(PvObj.SetParameter('minkvar', -Settings['KvarLimit']))
        self.__maxQ = float(PvObj.SetParameter('maxkvar', Settings['KvarLimit']))

        # MISC settings
        self.__cutin = Settings['%PCutin']
        self.__cutout = Settings['%PCutout']
        self.__trip_deadtime_sec = Settings['Reconnect deadtime - sec']
        self.__Time_to_Pmax_sec = Settings['Reconnect Pmax time - sec']
        self.__Prated = Settings['maxKW']
        self.__priority = Settings['Priority']
        self.__enablePFlimit = Settings['Enable PF limit']
        self.__minPF = Settings['pfMin']
        self.__UcalcMode = Settings['UcalcMode']
        # initialize deadtimes and other variables
        self.__initializeRideThroughSettings()
        if self.__Settings["Follow standard"] == "1547-2003":
            self.__rVs = [1.10, 0.88]
        else:
            self.__rVs, self.__rTs = self.__CreateOperationRegions()

        # For debugging only
        self.useAvgVoltage = False
        cycleAvg = 5
        freq = dssSolver.getFrequency()
        step = dssSolver.GetStepSizeSec()
        hist_size = math.ceil(cycleAvg / (step * freq))
        self.voltage = [1.0 for i in range(hist_size)]
        self.reactive_power = [0.0 for i in range(hist_size)]
        self.__VoltVioM = False
        self.__VoltVioP = False
        
        self.region = [3, 3, 3]
        
        self.voltage_hist = []
        self.power_hist = []
        self.timer_hist = []
        self.timer_act_hist = []
        
        return

    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.Class, self.Name)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]

    def __initializeRideThroughSettings(self):
        self.__isConnected = True
        self.__Plimit = self.__Prated
        self.__CutoffTime = self.__dssSolver.GetDateTime()
        self.__ReconnStartTime = self.__dssSolver.GetDateTime() - datetime.timedelta(
            seconds=int(self.__Time_to_Pmax_sec))

        self.__TrippedPmaxDelay = 0
        self.__NormOper = True
        self.__NormOperStartTime = self.__dssSolver.GetDateTime()
        self.__uViolationtime = 99999
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
            ov2pu_eq = 1.20
            ov2sec_eq = 0.16
            ov1pu_min = 1.1
            ov1pu_max = 1.2
            ov1sec_min = 1
            ov1sec_max = 13
            uv2pu_min = 0.0
            uv2pu_max = 0.5
            uv2sec_min = 0.16
            uv2sec_max = 2.0
            uv1pu_min = 0.0
            uv1pu_max = 0.88
            uv1sec_min = 2.0
            uv1sec_max = 21
    
            V = [1.10, 0.88, 0.7, 1.20, 1.175, 1.15, 0.5, 0.5]
            T = [1.5, 0.7, 0.2, 0.5, 1, 0.16, 0.16]
            self.__faultCounterMax = 2
            self.__faultCounterClearingTimeSec = 20

        elif self.__Settings['Ride-through Category'] == 'Category II':
            ov2pu_eq = 1.20
            ov2sec_eq = 0.16
            ov1pu_min = 1.1
            ov1pu_max = 1.2
            ov1sec_min = 1
            ov1sec_max = 13
            uv2pu_min = 0.0
            uv2pu_max = 0.45
            uv2sec_min = 0.16
            uv2sec_max = 2.0
            uv1pu_min = 0.0
            uv1pu_max = 0.88
            uv1sec_min = 2.0
            uv1sec_max = 21

            V = [1.10, 0.88, 0.65, 1.20, 1.175, 1.15, 0.45, 0.30]
            T = [5, 3, 0.2, 0.5, 1, 0.32, 0.16]
            self.__faultCounterMax = 2
            self.__faultCounterClearingTimeSec = 10

        elif self.__Settings['Ride-through Category'] == 'Category III':
            ov2pu_eq = 1.20
            ov2sec_eq = 0.16
            ov1pu_min = 1.1
            ov1pu_max = 1.2
            ov1sec_min = 1
            ov1sec_max = 13
            uv2pu_min = 0.0
            uv2pu_max = 0.5
            uv2sec_min = 2.0
            uv2sec_max = 21.0
            uv1pu_min = 0.0
            uv1pu_max = 0.88
            uv1sec_min = 2.0
            uv1sec_max = 21.0

            V = [1.10, 0.88, 0.5, 1.2, 1.2, 1.2, 0.0, 0.0]
            T = [21, 10, 13, 13, 13, 1, 1]
            self.__faultCounterMax = 3
            self.__faultCounterClearingTimeSec = 5

        #check overvoltage points
        if self.__Settings['OV2 - p.u.'] != ov2pu_eq:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['OV2 CT - sec'] != ov2sec_eq:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['OV1 - p.u.'] < ov1pu_min and self.__Settings['OV1 - p.u.'] > ov1pu_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['OV1 CT - sec'] < ov1sec_min and self.__Settings['OV1 CT - sec'] > ov1sec_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False
        #check undervoltage points
        if self.__Settings['UV2 - p.u.'] < uv2pu_min and self.__Settings['UV2 - p.u.'] > uv2pu_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['UV2 CT - sec'] < uv2sec_min and self.__Settings['UV2 CT - sec'] > uv2sec_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['UV1 - p.u.'] < uv1pu_min and self.__Settings['UV1 - p.u.'] > uv1pu_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.__Settings['UV1 CT - sec'] <uv1sec_min and self.__Settings['UV1 CT - sec'] > uv1sec_max:
            print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        self._ControlledElm.SetParameter('Model', '7')
        self._ControlledElm.SetParameter('Vmaxpu', V[0])
        self._ControlledElm.SetParameter('Vminpu', V[1])

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
                    self.CurrLimRegion = unary_union(
                        [PermissiveOVRegion, PermissiveUVRegion, MandatoryRegion, MayTripRegion])
                    self.MomentarySucessionRegion = None
                    self.TripRegion = unary_union([OVtripRegion, UVtripRegion])
                else:
                    self.CurrLimRegion = unary_union([PermissiveOVRegion, PermissiveUVRegion, MandatoryRegion])
                    self.MomentarySucessionRegion = None
                    self.TripRegion = unary_union([OVtripRegion, UVtripRegion, MayTripRegion])
            else:
                if self.__Settings['May trip operation'] == 'Permissive operation':
                    self.CurrLimRegion = MandatoryRegion
                    self.MomentarySucessionRegion = unary_union([PermissiveOVRegion, PermissiveUVRegion, MayTripRegion])
                    self.TripRegion = unary_union([OVtripRegion, UVtripRegion])
                else:
                    self.CurrLimRegion = MandatoryRegion
                    self.MomentarySucessionRegion = unary_union([PermissiveOVRegion, PermissiveUVRegion])
                    self.TripRegion = unary_union([OVtripRegion, UVtripRegion, MayTripRegion])
        else:
            if self.__Settings['May trip operation'] == 'Permissive operation':
                self.CurrLimRegion = MandatoryRegion
                self.MomentarySucessionRegion = unary_union([PermissiveOVRegion, PermissiveUVRegion, MayTripRegion])
                self.TripRegion = unary_union([OVtripRegion, UVtripRegion])
            else:
                self.CurrLimRegion = MandatoryRegion
                self.MomentarySucessionRegion = unary_union([PermissiveOVRegion, PermissiveUVRegion])
                self.TripRegion = unary_union([OVtripRegion, UVtripRegion, MayTripRegion])
        self.NormalRegion = ContineousRegion
        
        
        
        return V, T

    def Update(self, Priority, Time, Update):

        Error = 0
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = Time
        if Priority == 0:
            self.__isConnected = self.__Connect()
  
        if Priority == 2:
            uIn = self.__UpdateViolatonTimers()
            if self.__Settings["Follow standard"] == "1547-2018":
                self.VoltageRideThrough(uIn)
            elif self.__Settings["Follow standard"] == "1547-2003":
                self.Trip(uIn)
            else:
                raise Exception("Valid standard setting defined. Options are: 1547-2003, 1547-2018")
            
            P = -sum(self._ControlledElm.GetVariable('Powers')[::2])
            self.power_hist.append(P)
            self.voltage_hist.append(uIn)
            self.voltage_hist.append(uIn)
            self.timer_hist.append(self.__uViolationtime)
            self.timer_act_hist.append(self.__dssSolver.GetTotalSeconds())
        # if self.Time == 59 and Priority==2:
         
        #     if hasattr(self, "CurrLimRegion"):
            
        #         import matplotlib.pyplot as plt
        #         fig, (ax1, ax2) = plt.subplots(2,1)

        #         try:
        #             models = [MultiPolygon([self.CurrLimRegion]), self.MomentarySucessionRegion, self.TripRegion, MultiPolygon([self.NormalRegion])]
        #         except:
        #             try:
        #                 models = [self.CurrLimRegion, self.MomentarySucessionRegion, self.TripRegion, MultiPolygon([self.NormalRegion])]
        #             except:
        #                 try:
        #                     models = [MultiPolygon([self.CurrLimRegion]), self.MomentarySucessionRegion, self.TripRegion, self.NormalRegion]
        #                 except:
        #                     models = [self.CurrLimRegion, self.MomentarySucessionRegion, self.TripRegion, self.NormalRegion]
                        
        #         models = [i for i in models if i is not None]            
                
        #         colors = ["orange", "grey", "red", "green"]
        #         for m, c in zip(models, colors):
        #             for geom in m.geoms:    
        #                 xs, ys = geom.exterior.xy    
        #                 ax1.fill(xs, ys, alpha=0.35, fc=c, ec='none')
        #         ax1.set_xlim(0, 60)
        #         ax1.set_ylim(0, 1.20)
        #         ax1.scatter( self.timer_hist, self.voltage_hist)
        #         ax3 = ax2.twinx()
        #         ax2.set_ylabel('Power (kW) in green')
        #         ax3.set_ylabel('Voltage (p.u.) in red')
        #         ax2.plot(self.timer_act_hist[1:], self.power_hist[1:], c="green")
        #         ax3.plot(self.timer_act_hist[1:], self.voltage_hist[1:], c="red")
        #         fig.savefig(f"test.png")
        #         quit()

        return Error

    def Trip(self, uIn):
        """ Implementation of the IEEE1587-2003 voltage ride-through requirements for inverter systems
        """
        if uIn < 0.88:
            if self.__isConnected:
                self.__Trip(30.0, 0.4, False)
        return

    def VoltageRideThrough(self, uIn):
        """ Implementation of the IEEE1587-2018 voltage ride-through requirements for inverter systems
        """
        self.__faultCounterClearingTimeSec = 1

        Pm = Point(self.__uViolationtime, uIn)
        if Pm.within(self.CurrLimRegion):
            region = 0
            isinContioeousRegion = False
        elif self.MomentarySucessionRegion and Pm.within(self.MomentarySucessionRegion):
            region = 1
            isinContioeousRegion = False
            self.__Trip(self.__dssSolver.GetStepSizeSec(), 0.4, False)
        elif Pm.within(self.TripRegion):
            region = 2
            isinContioeousRegion = False
            if self.region == [3, 1, 1]:
                self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False, True)
            else: 
                self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False)
        else:
            isinContioeousRegion = True
            region = 3
            
        self.region = self.region[1:] + self.region[:1]
        self.region[0] = region

        if isinContioeousRegion and not self.__isinContioeousRegion:
            self.__FaultwindowClearingStartTime = self.__dssSolver.GetDateTime()
        clearingTime = (self.__dssSolver.GetDateTime() - self.__FaultwindowClearingStartTime).total_seconds()

        if self.__isinContioeousRegion and not isinContioeousRegion:
            if  clearingTime <= self.__faultCounterClearingTimeSec:
                self.__faultCounter += 1
                if self.__faultCounter > self.__faultCounterMax:
                    if self.__Settings['Multiple disturbances'] == 'Trip':
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
            uIn = self._ControlledElm.GetVariable('VoltagesMagAng')[::2]
            uBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
            uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
            if self.useAvgVoltage:
                self.voltage = self.voltage[1:] + self.voltage[:1]
                self.voltage[0] = uIn
                uIn = sum(self.voltage) / len(self.voltage)
            deadtime = (self.__dssSolver.GetDateTime() - self.__TrippedStartTime).total_seconds()
            if uIn < self.__rVs[0] and uIn > self.__rVs[1] and deadtime >= self.__TrippedDeadtime:
                
                self._ControlledElm.SetParameter('enabled', True)
                self.__isConnected = True
                self._ControlledElm.SetParameter('kw', 0)
                self.__ReconnStartTime = self.__dssSolver.GetDateTime()
        else:
            conntime = (self.__dssSolver.GetDateTime() - self.__ReconnStartTime).total_seconds()
            self.__Plimit = conntime / self.__TrippedPmaxDelay * self.__Prated if conntime < self.__TrippedPmaxDelay \
                else self.__Prated
            self._ControlledElm.SetParameter('kw', self.__Plimit)
        return self.__isConnected

    def __Trip(self, Deadtime, Time2Pmax, forceTrip, permissive_to_trip=False):
        
        uIn = self._ControlledElm.GetVariable('VoltagesMagAng')[::2]
        uBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
        
        #if self.Time >1:
        
        if self.__isConnected or forceTrip:
            print(self._ControlledElm.GetInfo(), uIn, uBase)
            self._ControlledElm.SetParameter('enabled', False)

            self.__isConnected = False
            self.__TrippedStartTime = self.__dssSolver.GetDateTime()
            self.__TrippedPmaxDelay = Time2Pmax
            self.__TrippedDeadtime = Deadtime
            
        elif permissive_to_trip:
            print(self._ControlledElm.GetInfo(), uIn, uBase)
            self._ControlledElm.SetParameter('enabled', False)

            self.__isConnected = False
            self.__TrippedStartTime = self.__dssSolver.GetDateTime()
            self.__TrippedPmaxDelay = Time2Pmax
            self.__TrippedDeadtime = Deadtime
        return

    def __UpdateViolatonTimers(self):
        uIn = self._ControlledElm.GetVariable('VoltagesMagAng')[::2]
        uBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
        if self.useAvgVoltage:
            self.voltage = self.voltage[1:] + self.voltage[:1]
            self.voltage[0] = uIn
            uIn = sum(self.voltage) / len(self.voltage)

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

from shapely.geometry import MultiPoint, Polygon, Point, MultiPolygon
from shapely.ops import triangulate, unary_union
import datetime
import math

from pydss.pyControllers.pyControllerAbstract import ControllerAbstract
from pydss.pyControllers.models import PvVoltageRideThruModel
from pydss.pyControllers.enumerations import PvStandard, VoltageCalcModes, RideThroughCategory, PermissiveOperation, MayTripOperation, MultipleDisturbances


class PvVoltageRideThru(ControllerAbstract):
    """Implementation of IEEE1547-2003 and IEEE1547-2018 voltage ride-through standards using the OpenDSS Generator model. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

            :param pv_object: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'Generator' element
            :type FaultObj: class:`pydss.dssElement.dssElement`
            :param settings: A dictionary that defines the settings for the PvController.
            :type settings: dict
            :param dss_instance: An :class:`opendssdirect` instance
            :type dss_instance: :class:`opendssdirect`
            :param elm_object_list: Dictionary of all dssElement, dssBus and dssCircuit objects
            :type elm_object_list: dict
            :param dss_solver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
            :type dss_solver: :mod:`pydss.SolveMode`
            :raises: Assertionerror if 'pv_object' is not a wrapped OpenDSS Generator element

    """

    def __init__(self, pv_object, settings, dss_instance, elm_object_list, dss_solver):
        super(PvVoltageRideThru, self).__init__(pv_object, settings, dss_instance, elm_object_list, dss_solver)

        self.model = PvVoltageRideThruModel(**settings)
        
        self.time_change = False
        self.time = (-1, 0)

        self.ControlDict = {
            'None': lambda: 0,
        }

        self._controlled_element = pv_object
        self.__dss_solver = dss_solver

        self.object_type, self.object_name = self._controlled_element.GetInfo()
        assert (self.object_type.lower() == 'generator'), 'PvControllerGen works only with an OpenDSS Generator element'
        self._name = 'pyCont_' + self.object_type + '_' + self.object_name
        if '_' in self.object_name:
            self.phase = self.object_name.split('_')[1]
        else:
            self.phase = None

        # Initializing the model
        pv_object.SetParameter('kvar', 0)
        pv_object.SetParameter('kva', self.model.kva)
        self._p_rated = float(pv_object.SetParameter('kW', self.model.max_kw))

        # MISC settings
        self._trip_deadtime_sec = self.model.reconnect_deadtime_sec
        self._time_to_p_max_sec = self.model.reconnect_pmax_time_sec
        self._p_rated = self.model.max_kw
        self._voltage_calc_mode = self.model.voltage_calc_mode
        # initialize deadtimes and other variables
        self._initialize_ride_through_settings()
        if self.model.follow_standard == PvStandard.IEEE_1547_2003:
            self._rvs = [1.10, 0.88]
        else:
            self._rvs, _= self._create_operation_regions()

        # For debugging only
        self.use_avg_voltage = False
        cycle_average = 5
        freq = dss_solver.getFrequency()
        step = dss_solver.GetStepSizeSec()
        hist_size = math.ceil(cycle_average / (step * freq))
        self.voltage = [1.0 for i in range(hist_size)]
        self.reactive_power = [0.0 for i in range(hist_size)]
        self._voltage_violation_m = False
        
        self.region = [3, 3, 3]
        
        # self.voltage_hist = []
        # self.power_hist = []
        # self.timer_hist = []
        # self.timer_act_hist = []
        
        return

    def Name(self):
        return self._name

    def ControlledElement(self):
        return "{}.{}".format(self.object_type, self.object_name)

    def debugInfo(self):
        return []

    def _initialize_ride_through_settings(self):
        self._is_connected = True
        self._p_limit = self._p_rated
        self._reconnect_start_time = self.__dss_solver.GetDateTime() - datetime.timedelta(
            seconds=int(self._time_to_p_max_sec))

        self._tripped_p_max_delay = 0
        self._normal_operation = True
        self._normal_operation_start_time = self.__dss_solver.GetDateTime()
        self._u_violation_time = 99999
        self._tripped_start_time = self.__dss_solver.GetDateTime()
        self._tripped_dead_time = 0
        self._fault_counter = 0
        self._is_in_contioeous_region = True
        self._fault_window_clearing_start_time = self.__dss_solver.GetDateTime()

        return

    def _create_operation_regions(self):
        u_max_theo = 10
        t_max = 1e10

        ov_trip_points = [
            Point(u_max_theo, self.model.ov_2_ct_sec),
            Point(self.model.ov_2_pu, self.model.ov_2_ct_sec),
            Point(self.model.ov_2_pu, self.model.ov_1_ct_sec),
            Point(self.model.ov_1_pu, self.model.ov_1_ct_sec),
            Point(self.model.ov_1_pu, t_max),
            Point(u_max_theo, t_max)
        ]
        ov_trip_region = Polygon([[p.y, p.x] for p in ov_trip_points])

        UVtripPoints = [
            Point(0, self.model.uv_2_ct_sec),
            Point(self.model.uv_2_pu, self.model.uv_2_ct_sec),
            Point(self.model.uv_2_pu, self.model.uv_1_ct_sec),
            Point(self.model.uv_1_pu, self.model.uv_1_ct_sec),
            Point(self.model.uv_1_pu, t_max),
            Point(0, t_max)
        ]
        uv_trip_region = Polygon([[p.y, p.x] for p in UVtripPoints])

        if self.model.ride_through_category == RideThroughCategory.CATEGORY_I:
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
            self._fault_counter_max = 2
            self._fault_counter_clearing_time_sec = 20

        elif self.model.ride_through_category == RideThroughCategory.CATEGORY_II:
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
            self._fault_counter_max = 2
            self._fault_counter_clearing_time_sec = 10

        elif self.model.ride_through_category == RideThroughCategory.CATEGORY_I:
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
            self._fault_counter_max = 3
            self._fault_counter_clearing_time_sec = 5

        #check overvoltage points
        if self.model.ov_2_pu != ov2pu_eq:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        
        if self.model.ov_2_ct_sec != ov2sec_eq:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.model.ov_1_pu < ov1pu_min and self.model.ov_1_pu > ov1pu_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.model.ov_1_ct_sec < ov1sec_min and self.model.ov_1_ct_sec > ov1sec_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False
        #check undervoltage points
        if self.model.uv_2_pu < uv2pu_min and self.model.uv_2_pu > uv2pu_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.model.uv_2_ct_sec < uv2sec_min and self.model.uv_2_ct_sec > uv2sec_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.model.uv_1_pu < uv1pu_min and self.model.uv_1_pu > uv1pu_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        if self.model.uv_1_ct_sec <uv1sec_min and self.model.uv_1_ct_sec > uv1sec_max:
            #print("User defined setting outside of IEEE 1547 acceptable range.")
            assert False

        self._controlled_element.SetParameter('Model', '7')
        self._controlled_element.SetParameter('Vmaxpu', V[0])
        self._controlled_element.SetParameter('Vminpu', V[1])

        contineous_points = [Point(V[0], 0), Point(V[0], t_max), Point(V[1], t_max), Point(V[1], 0)]
        contineous_region = Polygon([[p.y, p.x] for p in contineous_points])

        mandatory_points = [Point(V[1], 0), Point(V[1], T[0]), Point(V[2], T[1]), Point(V[2], 0)]
        mandatory_region = Polygon([[p.y, p.x] for p in mandatory_points])

        permissive_ov_points = [Point(V[3], 0), Point(V[3], T[2]), Point(V[4], T[2]), Point(V[4], T[3]),
                              Point(V[5], T[3]),
                              Point(V[5], T[4]), Point(V[0], T[4]), Point(V[0], 0.0)]
        permissive_ov_region = Polygon([[p.y, p.x] for p in permissive_ov_points])

        permissive_uv_points = [Point(V[2], 0), Point(V[2], T[5]), Point(V[6], T[5]), Point(V[6], T[6]),
                              Point(V[7], T[6]), Point(V[7], 0)]
        permissive_uv_region = Polygon([[p.y, p.x] for p in permissive_uv_points])

        active_region = MultiPolygon([ov_trip_region, uv_trip_region, contineous_region, mandatory_region,
                                     permissive_ov_region, permissive_uv_region])

        total_points = [Point(u_max_theo, 0), Point(u_max_theo, t_max), Point(0, t_max), Point(0, 0)]
        total_region = Polygon([[p.y, p.x] for p in total_points])
        intersection = total_region.intersection(active_region)
        may_trip_region = total_region.difference(intersection)

        if self.model.ride_through_category in [RideThroughCategory.CATEGORY_I, RideThroughCategory.CATEGORY_II]:
            if self.model.permissive_operation ==  PermissiveOperation.CURRENT_LIMITED:
                if self.model.may_trip_operation == MayTripOperation.PERMISSIVE_OPERATION:
                    self.curr_lim_region = unary_union(
                        [permissive_ov_region, permissive_uv_region, mandatory_region, may_trip_region])
                    self.momentary_sucession_region = None
                    self.trip_region = unary_union([ov_trip_region, uv_trip_region])
                else:
                    self.curr_lim_region = unary_union([permissive_ov_region, permissive_uv_region, mandatory_region])
                    self.momentary_sucession_region = None
                    self.trip_region = unary_union([ov_trip_region, uv_trip_region, may_trip_region])
            else:
                if self.model.may_trip_operation == MayTripOperation.PERMISSIVE_OPERATION:
                    self.curr_lim_region = mandatory_region
                    self.momentary_sucession_region = unary_union([permissive_ov_region, permissive_uv_region, may_trip_region])
                    self.trip_region = unary_union([ov_trip_region, uv_trip_region])
                else:
                    self.curr_lim_region = mandatory_region
                    self.momentary_sucession_region = unary_union([permissive_ov_region, permissive_uv_region])
                    self.trip_region = unary_union([ov_trip_region, uv_trip_region, may_trip_region])
        else:
            if self.model.may_trip_operation == MayTripOperation.PERMISSIVE_OPERATION:
                self.curr_lim_region = mandatory_region
                self.momentary_sucession_region = unary_union([permissive_ov_region, permissive_uv_region, may_trip_region])
                self.trip_region = unary_union([ov_trip_region, uv_trip_region])
            else:
                self.curr_lim_region = mandatory_region
                self.momentary_sucession_region = unary_union([permissive_ov_region, permissive_uv_region])
                self.trip_region = unary_union([ov_trip_region, uv_trip_region, may_trip_region])
        self.normal_region = contineous_region
        
        
        
        return V, T

    def Update(self, priority, time, update_results):

        error = 0
        self.time_change = self.time != (priority, time)
        self.time = time
        if priority == 0:
            self._is_connected = self._connect()
  
        if priority == 2:
            u_in = self._update_violaton_timers()
            if self.model.follow_standard == PvStandard.IEEE_1547_2018:
                self.voltage_ride_through(u_in)
            elif self.model.follow_standard == PvStandard.IEEE_1547_2003:
                self.trip(u_in)
            else:
                raise Exception("Valid standard setting defined. Options are: 1547-2003, 1547-2018")
            
            P = -sum(self._controlled_element.GetVariable('Powers')[::2])
            # self.power_hist.append(P)
            # self.voltage_hist.append(u_in)
            # self.timer_hist.append(self._u_violation_time)
            # self.timer_act_hist.append(self.__dss_solver.GetTotalSeconds())

        return error

    def trip(self, u_in):
        """ Implementation of the IEEE1587-2003 voltage ride-through requirements for inverter systems
        """
        if u_in < 0.88:
            if self._is_connected:
                self._trip(30.0, 0.4, False)
        return

    def voltage_ride_through(self, u_in):
        """ Implementation of the IEEE1587-2018 voltage ride-through requirements for inverter systems
        """
        self._fault_counter_clearing_time_sec = 1

        Pm = Point(self._u_violation_time, u_in)
        if Pm.within(self.curr_lim_region):
            region = 0
            is_in_contioeous_region = False
        elif self.momentary_sucession_region and Pm.within(self.momentary_sucession_region):
            region = 1
            is_in_contioeous_region = False
            self._trip(self.__dss_solver.GetStepSizeSec(), 0.4, False)
        elif Pm.within(self.trip_region):
            region = 2
            is_in_contioeous_region = False
            if self.region == [3, 1, 1]:
                self._trip(self._trip_deadtime_sec, self._time_to_p_max_sec, False, True)
            else: 
                self._trip(self._trip_deadtime_sec, self._time_to_p_max_sec, False)
        else:
            is_in_contioeous_region = True
            region = 3
            
        self.region = self.region[1:] + self.region[:1]
        self.region[0] = region

        if is_in_contioeous_region and not self._is_in_contioeous_region:
            self._fault_window_clearing_start_time = self.__dss_solver.GetDateTime()
        clearing_time = (self.__dss_solver.GetDateTime() - self._fault_window_clearing_start_time).total_seconds()

        if self._is_in_contioeous_region and not is_in_contioeous_region:
            if  clearing_time <= self._fault_counter_clearing_time_sec:
                self._fault_counter += 1
                if self._fault_counter > self._fault_counter_max:
                    if self.model.multiple_disturdances == MultipleDisturbances.TRIP: 
                        self._trip(self._trip_deadtime_sec, self._time_to_p_max_sec, True)
                        self._fault_counter = 0
                    else:
                        pass
        if  clearing_time > self._fault_counter_clearing_time_sec and self._fault_counter > 0:
            self._fault_counter = 0
        self._is_in_contioeous_region = is_in_contioeous_region
        return

    def _connect(self):
        if not self._is_connected:
            u_in = self._controlled_element.GetVariable('VoltagesMagAng')[::2]
            u_base = self._controlled_element.sBus[0].GetVariable('kVBase') * 1000
            u_in = max(u_in) / u_base if self._voltage_calc_mode == VoltageCalcModes.MAX else sum(u_in) / (u_base * len(u_in))
            if self.use_avg_voltage:
                self.voltage = self.voltage[1:] + self.voltage[:1]
                self.voltage[0] = u_in
                u_in = sum(self.voltage) / len(self.voltage)
            deadtime = (self.__dss_solver.GetDateTime() - self._tripped_start_time).total_seconds()
            if u_in < self._rvs[0] and u_in > self._rvs[1] and deadtime >= self._tripped_dead_time:
                
                self._controlled_element.SetParameter('enabled', True)
                self._is_connected = True
                self._controlled_element.SetParameter('kw', 0)
                self._reconnect_start_time = self.__dss_solver.GetDateTime()
        else:
            conntime = (self.__dss_solver.GetDateTime() - self._reconnect_start_time).total_seconds()
            self._p_limit = conntime / self._tripped_p_max_delay * self._p_rated if conntime < self._tripped_p_max_delay \
                else self._p_rated
            self._controlled_element.SetParameter('kw', self._p_limit)
        return self._is_connected

    def _trip(self, Deadtime, time2Pmax, forceTrip, permissive_to_trip=False):
        
        u_in = self._controlled_element.GetVariable('VoltagesMagAng')[::2]
        u_base = self._controlled_element.sBus[0].GetVariable('kVBase') * 1000
        u_in = max(u_in) / u_base if self._voltage_calc_mode == VoltageCalcModes.MAX else sum(u_in) / (u_base * len(u_in))

        if self._is_connected or forceTrip:
            self._controlled_element.SetParameter('enabled', False)

            self._is_connected = False
            self._tripped_start_time = self.__dss_solver.GetDateTime()
            self._tripped_p_max_delay = time2Pmax
            self._tripped_dead_time = Deadtime
            
        elif permissive_to_trip:
            self._controlled_element.SetParameter('enabled', False)

            self._is_connected = False
            self._tripped_start_time = self.__dss_solver.GetDateTime()
            self._tripped_p_max_delay = time2Pmax
            self._tripped_dead_time = Deadtime
        return

    def _update_violaton_timers(self):
        u_in = self._controlled_element.GetVariable('VoltagesMagAng')[::2]
        u_base = self._controlled_element.sBus[0].GetVariable('kVBase') * 1000
        u_in = max(u_in) / u_base if self._voltage_calc_mode == VoltageCalcModes.MAX else sum(u_in) / (u_base * len(u_in))
        if self.use_avg_voltage:
            self.voltage = self.voltage[1:] + self.voltage[:1]
            self.voltage[0] = u_in
            u_in = sum(self.voltage) / len(self.voltage)

        if u_in < self._rvs[0] and u_in > self._rvs[1]:
            if not self._normal_operation:
                self._normal_operation = True
                self._normal_operation_start_time = self.__dss_solver.GetDateTime()
                self._normal_operation_time = 0
            else:
                self._normal_operation_time = (self.__dss_solver.GetDateTime() - self._normal_operation_start_time).total_seconds()
            self._voltage_violation_m = False
        else:
            if not self._voltage_violation_m:
                self._voltage_violation_m = True
                self.__uViolationstarttime = self.__dss_solver.GetDateTime()
                self._u_violation_time = 0
            else:
                self._u_violation_time = (self.__dss_solver.GetDateTime() - self.__uViolationstarttime).total_seconds()
        return u_in

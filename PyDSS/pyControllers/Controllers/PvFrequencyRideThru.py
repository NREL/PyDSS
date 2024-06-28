from ipaddress import v4_int_to_packed
from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
from shapely.geometry import MultiPoint, Polygon, Point, MultiPolygon
from shapely.ops import triangulate, cascaded_union
import matplotlib.pyplot as plt
import datetime
import math
import os
from pydantic import BaseModel, validator, conint, confloat
import pdb
import numpy as np
import scipy.signal as signal

class PvFrequencyRideThru(ControllerAbstract):
    """Implementation of IEEE1547-2003 and IEEE1547-2018 frequency ride-through and frequency droop standards using the OpenDSS Generator model. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

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
        super(PvFrequencyRideThru, self).__init__(PvObj, Settings, dssInstance, ElmObjectList, dssSolver)

        self.TimeChange = False
        self.Time = (-1, 0)

        self._ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None': lambda: 0,
        }

        self._ControlledElm = PvObj
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.Class, self.Name = self._ControlledElm.GetInfo()
        assert (self.Class.lower() == 'generator'), 'PvControllerGen works only with an OpenDSS Generator element'
        self.__Name = 'pyCont_' + self.Class + '_' + self.Name
        if '_' in self.Name:
            self.Phase = self.Name.split('_')[1]
        else:
            self.Phase = None
            
        #TIME
        self.__Step= dssSolver.GetStepSizeSec()
        self.T=[0,dssSolver.GetStepResolutionSeconds()]

        #SETTINGS
        self.__Prated = float(self._ControlledElm.GetParameter('kw'))
        self.__Pmargin=float(self.__Settings["Reserve Margin"])
        self.__Preserved = float(self._ControlledElm.SetParameter('kw',self.__Prated*(1-self.__Pmargin)))
        self.__Tpord = float(self.__Settings["T_pord"])
        self.__Trf = float(self.__Settings["T_rf"])
        self.__Large_signal_limited=bool(self.__Settings["Large_signal_limited"])
        self.__Large_signal_ramp=(0.2*self.__Prated)*(self.__Step/60) #Large-signal limitation per timestep
        self.__trip_deadtime_sec = Settings['Reconnect deadtime - sec']
        self.__Time_to_Pmax_sec = Settings['Reconnect Pmax time - sec']
        self.__UcalcMode = Settings['UcalcMode']
        self.__db_UF = self.__Settings['db_UF']
        self.__db_OF = self.__Settings['db_OF']
        self.__k_UF = self.__Settings['k_UF']
        self.__k_OF = self.__Settings['k_OF']

        self.__testing_block_enabled =self.__Settings['Testing block enabled']

        #INITIAL DEADTIMES AND OPERATING REGIONS
        self.__initializeRideThroughSettings() #set initial settings
        if self.__Settings["Follow standard"] == "1547-2018": 
            self.__CreateOperationRegions() #create polygons that represent the operating regions in 1547-18
        
        # INITIAL CONDITIONS
        self.f_start = dssSolver.getFrequency()
        self.u_ang = self._ControlledElm.GetVariable('VoltagesMagAng')[1::2][0] #get voltage angles (of first phase)
        self.p_start=float(self._ControlledElm.GetParameter('kw'))
        self.q_start=float(self._ControlledElm.GetParameter('kvar'))
        self.df = 0 #for ROCOF
        self.Droop_Enabled=False #start out with droop not enabled (i.e. can't provide droop on the first timestep)

        #MEASUREMENT STRATEGIES (see 1547 for guidance)
        self.useAvgVoltage = True #these will cause it to keep track of a list of voltage/frequency and update the first value and drop the last one every time step
        self.useAvgFrequency = False #these will cause it to keep track of a list of voltage/frequency and update the first value and drop the last one every time step
        #NOTE: 1547-2018 DOES NOT required the use of average frequency, only a required ACCURACY across a 5 cycle window. This controller will not use average frequency. 
        #NOTE: 1547-2018 DOES required an average ROCOF over an averaging window of AT LEAST 100 ms (6 cycles). This controller will assume this does not apply if >3 cycle simulation timestep. 
        if self.__Step<0.05:
            self.cycleAvg = 6 #do 0.1 sec average window to get the required number of steps in histogram
        else:
            self.cycleAvg=2*self.__Step*self.f_start #just do two timesteps if self.__Step is greater than 0.05 (sec
    
        #Create measurement windows for averaging per 1547-2018. Using the same size for all quantities for now.
        hist_size = math.ceil(self.cycleAvg / (self.__Step * self.f_start))
        self.frequency = [60.0 for i in range(hist_size)]
        self.voltage = [1.0 for i in range(hist_size)]
        self.rocof = [0.0 for i in range(hist_size)]
        self.reactive_power = [0.0 for i in range(hist_size)]

        self.region = [3, 3, 3]

        #PLOTTING
        self.frequency_hist = []
        self.measured_frequency_hist=[]
        self.rocof_hist=[]
        self.dp_hist=[]
        self.power_hist = []
        self.timer_hist = []
        self.timer_act_hist = []
        self.start_control=0
        self.end_control=0
        self.control_request=0
        
        #INITIALIZE FREQUENCY MEASUREMENT TRANSFER FUNCTION
        self.F=[self.f_start,self.f_start]
        self.frequency_measurement_transfer_function=signal.TransferFunction([1],[self.__Trf, 1]) #first-order transfer function
        self.f_out_prev=self.f_start * self.__Trf #spin up state vector
        
        # INITIALIZE DER RESPONSE TRANSFER FUNCTION
        self.P=[self.p_start,self.p_start]
        self.droop_controller_transfer_function = signal.TransferFunction([1], [self.__Tpord, 1]) #first-order transfer function
        self.p_out_prev= self.p_start * self.__Tpord #spin up state vector

        return

    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.Class, self.Name)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]
    
    def DroopController(self, p_signal_input):

        self.P=[self.P[-1],p_signal_input]# set to last step kvar and the desired next step for controller input
        _,self.P_response,p_state_vector=signal.lsim2(self.droop_controller_transfer_function,self.P,self.T,self.p_out_prev) #run through our transfer function to get system response
        self.p_out_prev=p_state_vector[-1] #record evolution of state vector for use in next step initial condition
        pOut=self.P_response[-1] #return the control response

        return pOut
    
    def FrequencyMeasurement(self, f_signal_input):

        self.F=[self.F[-1],f_signal_input]# set to last step kvar and the desired next step for controller input
        _,self.F_response,f_state_vector=signal.lsim2(self.frequency_measurement_transfer_function,self.F,self.T,self.f_out_prev) #run through our transfer function to get system response
        self.f_out_prev=f_state_vector[-1] #record evolution of state vector for use in next step initial condition
        fOut=self.F_response[-1] #return the control response

        return fOut

    def __initializeRideThroughSettings(self):

        # Initialize conditions 
        self.__isConnected = True #generator is connected
        if self.__Preserved < self.__Prated: #if we have defined a reserve margin, then set the Plimit to that reduced value
            self.__Plimit = self.__Preserved
        else: #if we haven't defined a reserve margin, then keep P limit as the generator rating
            self.__Plimit = self.__Prated
            
        self.__ReconnStartTime = self.__dssSolver.GetDateTime() - datetime.timedelta(seconds=int(self.__Time_to_Pmax_sec)) #reconnecting at the beginning of the simulation? Reconnecting at self.__Time_to_Pmax_sec before the start of the simulation. 

        self.__TrippedPmaxDelay = 0 #Controls the ramp rate during enter service period
        self.__NormOper = True #within continuous bounds
        self.__NormOperStartTime = self.__dssSolver.GetDateTime() #Start of when we entered continuous bounds
        self.__fViolationtime = 99999 # this is the violation timer. This gets updated to 0 once we hit our first frequency violation
        self.__TrippedStartTime = self.__dssSolver.GetDateTime() # I think this is arbitrary at initialization. This gets set to the current time when the DER trips. 
        self.__TrippedDeadtime = 0 #gets reset when we trip the DER
        self.__faultCounter = 0 #used to assess multiple disturbances
        self.__isinContinuousRegion = True #tracking if we are in the continuous operating region
        self.__FaultwindowClearingStartTime = self.__dssSolver.GetDateTime()  #used to keep track of time under fault condition. This is reset when there is a fault registered and it is cleared. 
        self.__continuous_f_upper = 61.2 #upper threshold for continuous region
        self.__continuous_f_lower = 58.8 #lower threholds for continuous region
        return

    def __CreateOperationRegions(self):
        fMaxTheo = 100
        tMax = 1e10

        #define the over frequency shall-trip region
        OFtripPoints = [
            Point(fMaxTheo, self.__Settings['OF2 CT - sec']),
            Point(self.__Settings['OF2 - Hz'], self.__Settings['OF2 CT - sec']),
            Point(self.__Settings['OF2 - Hz'], self.__Settings['OF1 CT - sec']),
            Point(self.__Settings['OF1 - Hz'], self.__Settings['OF1 CT - sec']),
            Point(self.__Settings['OF1 - Hz'], tMax),
            Point(fMaxTheo, tMax)
        ]
        OFtripRegion = Polygon([[p.y, p.x] for p in OFtripPoints])

        #define the under frequency shall-trip region
        UFtripPoints = [
            Point(0, self.__Settings['UF2 CT - sec']),
            Point(self.__Settings['UF2 - Hz'], self.__Settings['UF2 CT - sec']),
            Point(self.__Settings['UF2 - Hz'], self.__Settings['UF1 CT - sec']),
            Point(self.__Settings['UF1 - Hz'], self.__Settings['UF1 CT - sec']),
            Point(self.__Settings['UF1 - Hz'], tMax),
            Point(0, tMax)
        ]
        UFtripRegion = Polygon([[p.y, p.x] for p in UFtripPoints])

        if self.__Settings['Ride-through Category'] in ['Category I', 'Category II', 'Category III']:

            #check over frequency points
            if self.__Settings['OF2 - Hz'] < 61.8 or self.__Settings['OF2 - Hz'] > 66:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['OF2 CT - sec'] < 0.16 or self.__Settings['OF2 CT - sec'] > 1000:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['OF1 - Hz'] < 61.0 or self.__Settings['OF1 - Hz'] > 66.0:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['OF1 CT - sec'] <180 or self.__Settings['OF1 CT - sec'] > 1000:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False
            #check under frequency points
            if self.__Settings['UF2 - Hz'] > 57.0 or self.__Settings['UF2 - Hz'] < 50:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['UF2 CT - sec'] < 0.16 or self.__Settings['UF2 CT - sec'] > 1000:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['UF1 - Hz'] < 50 or self.__Settings['UF1 - Hz'] > 59.0:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            if self.__Settings['UF1 CT - sec'] < 180 or self.__Settings['UF1 CT - sec'] > 1000:
                print("User defined setting outside of IEEE 1547 acceptable range.")
                assert False

            self.__faultCounterMax = 2
            self.__faultCounterClearingTimeSec = 20

        else:
            print("Unknown Standard.")
            assert False

        if self.__Settings['Ride-through Category'] == 'Category I':
            self.__max_rocof = 0.5 #hz/sec
            # self.__max_rocof = 1 #hz/sec
        elif self.__Settings['Ride-through Category'] == 'Category II':
            self.__max_rocof = 2.0 #hz/sec
        elif self.__Settings['Ride-through Category'] == 'Category III':
            self.__max_rocof = 3.0 #hz/sec


        self._ControlledElm.SetParameter('Model', '7')
        self._ControlledElm.SetParameter('Class', '0')


        ContinuousPoints = [Point(self.__continuous_f_upper, 0), Point(self.__continuous_f_upper, tMax), Point(self.__continuous_f_lower, tMax), Point(self.__continuous_f_lower, 0)]
        ContinuousRegion = Polygon([[p.y, p.x] for p in ContinuousPoints])

        MandatoryPoints1 = [Point(61.8, 0), Point(61.8, 299), Point(self.__continuous_f_upper, 299), Point(self.__continuous_f_upper, 0)]
        MandatoryRegion1 = Polygon([[p.y, p.x] for p in MandatoryPoints1]) #todo: could define these numbers in variables but they are not configurable by user.

        MandatoryPoints2 = [Point(self.__continuous_f_lower, 0), Point(self.__continuous_f_lower, 299), Point(57.0, 299), Point(57.0, 0)]
        MandatoryRegion2 = Polygon([[p.y, p.x] for p in MandatoryPoints2]) #todo: could define these numbers in variables but they are not configurable by user.

        ActiveRegion = MultiPolygon([OFtripRegion, UFtripRegion, ContinuousRegion, 
                                    MandatoryRegion1,MandatoryRegion2])


        TotalPoints = [Point(fMaxTheo, 0), Point(fMaxTheo, tMax), Point(0, tMax), Point(0, 0)]
        TotalRegion = Polygon([[p.y, p.x] for p in TotalPoints])
        intersection = TotalRegion.intersection(ActiveRegion)
        MayTripRegion = TotalRegion.difference(intersection) #everything not in the active region is the white "may trip" 

        if self.__Settings['May trip operation'] == 'Trip':
            self.CurrLimRegion = cascaded_union([MandatoryRegion1, MandatoryRegion2]) #Naming probably not appropriate with frequency variation.  
            self.TripRegion = cascaded_union([OFtripRegion, UFtripRegion, MayTripRegion])
        elif self.__Settings['May trip operation'] == 'Ride-Through':
            self.CurrLimRegion = cascaded_union([MandatoryRegion1, MandatoryRegion2, MayTripRegion])
            self.TripRegion = cascaded_union([OFtripRegion, UFtripRegion])
        else:
            print('unknown ride-through setting')
            assert False
        self.ContinuousRegion = ContinuousRegion
        return 

    def calculate_frequency(self, priority, time):
 
        vsrc = self._ElmObjectList["Vsource.source"]
        u_ang = vsrc.GetParameter("angle")
        u_ang = u_ang * math.pi / 180
        # if priority == 2:
        if time <= 1:
            bus_freq = self.__dssSolver.getFrequency()
            self.u_ang = u_ang
        else:
            h = self.__dssSolver.GetStepSizeSec()
            tau = h * 4
            dphi = (u_ang - self.u_ang) / (2 * math.pi * h)
            self.df = (dphi + self.df * (tau / h) ) / ( 1 + tau / h )    
            base_freq = self.__dssSolver.getFrequency()
            bus_freq = base_freq + self.df 
            self.u_ang = u_ang
        
        if self.__testing_block_enabled:
            bus_freq=self.Testing_Block(time)

        measured_freq=self.FrequencyMeasurement(bus_freq)
        self.frequency_hist.append(bus_freq)
        self.measured_frequency_hist.append(measured_freq)
        
        return measured_freq

    def calculate_rocof(self):
        df = abs(self.frequency[0] - self.frequency[1])
        self.rocof.insert(0,df/self.__Step)
        self.rocof.pop()
        avg_rocof = sum(self.rocof)/len(self.rocof)
        return avg_rocof

    def Update(self, Priority, Time, Update):
        Error = 0
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = Time
        if Priority == 0:
            if self.Time == 0: #if first timestep, get the voltage angles
                self.u_ang = self._ControlledElm.GetVariable('VoltagesMagAng')[1::2][0]
        if Priority == 2: 
            self.T=[self.T[-1],float(self.__dssSolver.GetTotalSeconds())]
            self.freq = self.calculate_frequency(Priority, Time)
            self.__isConnected = self.__Connect() #This shouldn't change kW value if self.Droop_Enabled
            self.connect_test=self.__isConnected
            self.avg_rocof = self.calculate_rocof()
            # pIn = -sum(self._ControlledElm.GetVariable('Powers')[::2])
            pIn=float(self._ControlledElm.GetParameter('kw'))
            fIn = self.__UpdateViolatonTimers()
            if self.__Settings["Follow standard"] == "1547-2018":
                pOut = self.FrequencyRideThrough(fIn, pIn)
            elif self.__Settings["Follow standard"] == "1547-2003":
                pOut=self.Trip(fIn,pIn)
            else:
                raise Exception("Valid standard setting defined. Options are: 1547-2003, 1547-2018")
            if self.__isConnected:
                self._ControlledElm.SetParameter('kw', pOut)
        
            if not self.dp_hist:
                self.dp_hist.append(0)
                # self.rocof_hist.append(0)
            else:
                self.dp_hist.append((pOut-self.power_hist[-1])/self.__Prated/self.__Step)
                # self.rocof_hist.append((fIn-self.measured_frequency_hist[-2])/self.__Step)
            self.rocof_hist.append(self.avg_rocof)
            self.power_hist.append(pOut)
            self.timer_hist.append(self.__fViolationtime)
            self.timer_act_hist.append(self.__dssSolver.GetTotalSeconds())

        # if self.Time == 59 and Priority==2: # Time is the time step, 
        #     self.Plotting()
           
        return Error

    def Trip(self, fIn, pIn):
        """ Implementation of the IEEE1547-2003 voltage ride-through requirements for inverter systems
        """
        if fIn < 59.3 or fIn > 60.5: # see page 9 of 1547-2003. #todo: more parameters are possible.  
            if self.__isConnected:
                self.__Trip(300.0, 0.16, False)
            pOut=0
        else:
            pOut=pIn
        return pOut

    def FrequencyRideThrough(self, fIn, pIn):
        """ Implementation of the IEEE1587-2018 voltage ride-through requirements for inverter systems
        """
        self.__faultCounterClearingTimeSec = 1
        Pm = Point(self.__fViolationtime, fIn)
        if Pm.within(self.CurrLimRegion):
            region = 0
            isinContinuousRegion = False
            if self.Droop_Enabled:
                pOut = self.__Frequency_Droop(fIn, pIn)
            else:
                pOut = pIn

        elif Pm.within(self.TripRegion):
            region = 2
            isinContinuousRegion = False
            if self.region == [3, 1, 1]: #Why? What is this region logic?
                self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False, True)
            else: 
                self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False)
            pOut = pIn
        else:
            isinContinuousRegion = True
            region = 3
            if self.Droop_Enabled:
                pOut = self.__Frequency_Droop(fIn, pIn)
            else:
                pOut = pIn
            #check if v/f > 1.1.  If it is, trip the DER. 
            u_pu = self.__UpdateVoltage()
            f_pu = fIn/60.0
            if u_pu/f_pu  > 1.1: #note: this is a very conservative interpretation of the standard. See table 19 (note c) and section 6.5.2.2
                self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False)

        #rocof
        if self.avg_rocof > self.__max_rocof:
            self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, False) #todo: not using function right. 

        self.region = self.region[1:] + self.region[:1]
        self.region[0] = region

        #if we were not originally in a continous region and we transitioned to a continous region, reset the fault timer counter
        if isinContinuousRegion and not self.__isinContinuousRegion:
            self.__FaultwindowClearingStartTime = self.__dssSolver.GetDateTime()
        
        clearingTime = (self.__dssSolver.GetDateTime() - self.__FaultwindowClearingStartTime).total_seconds() #Keep track of time under fault conditions.  

        #if we were in a continuous region and transition to fault region
        if self.__isinContinuousRegion and not isinContinuousRegion:
            if  clearingTime <= self.__faultCounterClearingTimeSec: # faultCounterClearingTimeSec is set to 1 in this function. Is this logic right??  
                self.__faultCounter += 1
                if self.__faultCounter > self.__faultCounterMax:
                    if self.__Settings['Multiple disturbances'] == 'Trip':
                        self.__Trip(self.__trip_deadtime_sec, self.__Time_to_Pmax_sec, True)
                        self.__faultCounter = 0
                    else:
                        pass
        if  clearingTime > self.__faultCounterClearingTimeSec and self.__faultCounter > 0:
            self.__faultCounter = 0
        self.__isinContinuousRegion = isinContinuousRegion
        return pOut
    

    def __Frequency_Droop(self, fIn, pIn):
        minKW = 0
        maxKW = self.__Prated
        pcalc=0

        #UNDERFREQUENCY
        if fIn < (60 - self.__db_UF):
            if self.__Settings["Ride-through Category"] == "Category I" and not self.__Settings["Category I Low Frequency Droop"]: #Cat I has optional droop control for UF
                pOut = pIn
            else:
                pcalc=min(self.__Plimit + (60-self.__db_UF-fIn)/(60*self.__k_UF) , maxKW)
                if self.__Large_signal_limited and pcalc>(1.05*self.__Plimit):
                    pOut=min(pIn+self.__Large_signal_ramp,maxKW)
                else:
                    
                    pOut = self.DroopController(pcalc)
        
        #OVERFREQUENCY
        elif fIn > (60 + self.__db_OF):
            pcalc=max(self.__Plimit - (fIn-60-self.__db_OF)/(60*self.__k_OF), minKW)
            if self.__Large_signal_limited and pcalc<(0.95*self.__Plimit):
                pOut=max(pIn-self.__Large_signal_ramp,minKW)
            else:
                pOut=self.DroopController(pcalc)

        else:
            pOut=self.DroopController(self.__Plimit)

        #PLOTTING DATA
        if (fIn < (60 - self.__db_UF) or fIn > (60 + self.__db_OF)) and self.start_control == 0:
            self.start_control=self.__dssSolver.GetTotalSeconds()
            self.control_request=pcalc-self.__Plimit

        if self.start_control != 0 and abs(pOut-self.__Preserved) >= abs(0.9*self.control_request) and self.end_control == 0:
                self.end_control=self.__dssSolver.GetTotalSeconds()
        return pOut

    def __Connect(self):
        self.frequency.insert(0,self.freq)
        self.frequency.pop()
        if self.useAvgFrequency:
            fIn = sum(self.frequency) / len(self.frequency) #get the average frequency across our measurement window
        else:
            fIn = self.freq
        if not self.__isConnected:# if the generator is not connected
            #In = self._ControlledElm.GetVariable('VoltagesMagAng')[::2]
            deadtime = (self.__dssSolver.GetDateTime() - self.__TrippedStartTime).total_seconds() #when not connected keep track of how long it is tripped for
            if fIn < self.__continuous_f_upper and fIn > self.__continuous_f_lower and deadtime >= self.__TrippedDeadtime: #if frquency is inside of the continuous region and we have exceeded the dead time we will reconnect
                self.__isConnected = True 
                self._ControlledElm.SetParameter('kw', 0) #start it at 0 kW so it can ramp back up
                self._ControlledElm.SetParameter('kvar',self.q_start) #do we need to ramp kvar too? I don't think so...?
                self._ControlledElm.SetParameter('class',0)
                self.__ReconnStartTime = self.__dssSolver.GetDateTime() #record the time it reconnected. 
            self.Droop_Enabled=False
        else: #if the generator IS connected
            conntime = (self.__dssSolver.GetDateTime() - self.__ReconnStartTime).total_seconds() #record how long it has been reconnected for
            if conntime < self.__TrippedPmaxDelay: # if we are still in the ramping timeframe
                self.__Plimit = conntime / self.__TrippedPmaxDelay * self.__Preserved #set our plimit to that allowed ramp rate
                self.Droop_Enabled=False # Do not allow Droop during the ramp 
            elif not self.Droop_Enabled: #if droop not enabled due to being in the ramping period and we are now no longer in ramp, we just reset Plimit to Preserved 
                self.__Plimit = self.__Preserved
                self.Droop_Enabled=True
                self._ControlledElm.SetParameter('kw', self.__Plimit)
            else: 
                pass
        return self.__isConnected

    def __Trip(self, Deadtime, Time2Pmax, forceTrip, permissive_to_trip=False):
        #Why? Is this logic right?  They look the same?
        if self.__isConnected or forceTrip:

            self._ControlledElm.SetParameter('kw',0)
            self._ControlledElm.SetParameter('kvar',0)
            self._ControlledElm.SetParameter('class',1)

            self.__isConnected = False
            self.__TrippedStartTime = self.__dssSolver.GetDateTime() #reset the tripped start time
            self.__TrippedPmaxDelay = Time2Pmax
            self.__TrippedDeadtime = Deadtime
            
        elif permissive_to_trip:

            self._ControlledElm.SetParameter('kw',0)
            self._ControlledElm.SetParameter('kvar',0)
            self._ControlledElm.SetParameter('class',1)

            self.__isConnected = False
            self.__TrippedStartTime = self.__dssSolver.GetDateTime()
            self.__TrippedPmaxDelay = Time2Pmax
            self.__TrippedDeadtime = Deadtime
        return

    
    def __UpdateViolatonTimers(self):

        fIn = self.freq 
        self.frequency.insert(0,fIn)
        self.frequency.pop()
        if self.useAvgFrequency:
            fIn = sum(self.frequency) / len(self.frequency)
        else:
            fIn = self.freq

        #track how long we've been operating under normal or abnormal conditions
        if fIn < self.__continuous_f_upper and fIn > self.__continuous_f_lower:
            if not self.__NormOper:
                self.__NormOper = True
                self.__NormOperStartTime = self.__dssSolver.GetDateTime()
                self.__NormOperTime = 0
            else:
                self.__NormOperTime = (self.__dssSolver.GetDateTime() - self.__NormOperStartTime).total_seconds()
            self.__FreqVioM = False # no violation
            # self.__VoltVioP = False

        else: #not in continuous region
            if not self.__FreqVioM: #if first step within violation
                self.__FreqVioM = True #frequency violation is true
                self.__fViolationstartTime = self.__dssSolver.GetDateTime() #note the violation start time
                self.__fViolationtime = 0 #start violation timer
            else: #if not the first step within violation
                self.__fViolationtime = (self.__dssSolver.GetDateTime() - self.__fViolationstartTime).total_seconds() #update the frequency violation timer. 


        return fIn


    def __UpdateVoltage(self):
        uIn = self._ControlledElm.GetVariable('VoltagesMagAng')[::2]
        uBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        uIn = max(uIn) / uBase if self.__UcalcMode == 'Max' else sum(uIn) / (uBase * len(uIn))
        if self.useAvgVoltage:
            self.voltage.insert(0,uIn)
            self.voltage.pop()
            uIn = sum(self.voltage) / len(self.voltage)
        return uIn
    
    def Testing_Block(self,time):

        #Pytest --> OVERWRITING THIS WILL RESULT IN FAILED PYTESTS
        if time >=1 and time <=10:
            bus_freq=60+(time*0.2)
        elif time >=11 and time <=20:
            bus_freq=62-((time-10)*0.2)
        else:
            bus_freq=60
        #######################################################################################################################################
        ##CONTINGENCY EVENT
        # over_under='over'
        # # over_under='under'
        # offset=5
        # if time < offset:
        #     bus_freq = 60
        # else:
        #     if over_under=='under':
        #         sharpness=0.12
        #         gradualness=0.01
        #         scaling=55
        #         bus_freq=60-(scaling*np.exp(-sharpness * (time-offset)) * (1 - np.exp(-gradualness * (time-offset))))
        #     else:
        #         sharpness=0.11
        #         gradualness=0.1
        #         scaling=4.5
        #         bus_freq=60+(scaling*np.exp(-sharpness * (time-offset)) * (1 - np.exp(-gradualness * (time-offset))))
        #######################################################################################################################################
        #LINEAR AND STEP CHANGE
        # # over_under='over'
        # over_under='under'
        # offset=5
        # # if time < offset:
        # #     bus_freq = 60
        # # else:
        # #     if over_under=='under':
        # #        bus_freq=59.1
        # #     else:
        # #        bus_freq=60.9

        # if time < offset:
        #     bus_freq = 60
        # else:
        #     if over_under=='under':
        #         bus_freq=60-(0.3*(time-offset))
        #     else:
        #         bus_freq=60+(0.3*(time-offset))
    #######################################################################################################################################
        return bus_freq
    
    def Plotting(self):
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2,2,figsize=(10,5))


        models = [self.CurrLimRegion, self.TripRegion, MultiPolygon([self.ContinuousRegion])]                    
        models = [i for i in models if i is not None]      
        
        colors = ["orange", "red", "green"]
        for m, c in zip(models, colors):
            for geom in m.geoms:    
                xs, ys = geom.exterior.xy    
                axes[0,0].fill(xs, ys, alpha=0.35, fc=c, ec='none')

        ax_twin=axes[0,1].twinx()

        axes[0,0].plot(self.timer_act_hist, self.frequency_hist, c='red', label='Frequency (Hz)')
        axes[0,1].plot(self.timer_act_hist, self.frequency_hist, c="black", linestyle=':',label='Bus Frequency (Hz)')
        axes[0,1].plot(self.timer_act_hist, self.measured_frequency_hist, c="red", label='Measured Frequency (Hz)')
        ax_twin.plot(self.timer_act_hist, self.power_hist, c="green", label='Active Power (kW)')
        axes[1,0].plot(self.timer_act_hist, self.rocof_hist,c='orange', label= 'Average ROCOF (Hz/s)')
        axes[1,1].plot(self.timer_act_hist, self.dp_hist,c='blue', label='delta P (% nameplate/s)')

        # ax_twin.axvline(x=self.start_control, color='black', linestyle='--')
        # ax_twin.axvline(x=self.end_control, color='blue', linestyle='--')

        # y_pos=sum(ax_twin.get_ylim())/2
        # ax_twin.annotate(
        #     '',
        #     xy=(self.start_control, y_pos), xycoords='data',
        #     xytext=(self.end_control, y_pos), textcoords='data',
        #     arrowprops=dict(arrowstyle='<->', color='red')
        # )
        # ax_twin.text((self.start_control + self.end_control) / 2, y_pos + 0.1, f'{self.end_control - self.start_control} s', color='red', ha='center')

        axes[0,0].set_ylim(56,63)
        axes[0,0].set_xlim(0, max(self.timer_act_hist))
        if max(self.power_hist)-min(self.power_hist)<1:
            # ax_twin.set_ylim(7,10.5)
            axes[1,1].set_ylim(-1,1)

        from matplotlib.ticker import ScalarFormatter
        
        
        axes[0,0].set_ylabel('Frequency (Hz)')
        axes[0,1].set_ylabel('Frequency (Hz)')
        ax_twin.set_ylabel('Power (kW)')
        axes[1,0].set_ylabel('Average ROCOF (Hz/sec)')
        axes[1,1].set_ylabel('dP (% nameplate/sec)')

        axes[0,0].grid(True)
        axes[0,0].legend()
        axes[0,1].grid(True)
        axes[0,1].legend(loc='upper right')
        ax_twin.grid(True)
        ax_twin.legend(loc='lower right')
        axes[1,0].grid(True)
        axes[1,0].legend()
        axes[1,1].grid(True)
        axes[1,1].legend()
        axes[0,1].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[1,1].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        fig.tight_layout()

        fig.savefig(f"C:/Users/epohl/Desktop/PROJECT_FILES/NAERM/Modeling/Frequency_Plots/{self.__Name}_{self.__Settings['Ride-through Category']}_test.png")


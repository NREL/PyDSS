#QSTS Model for Dynamic Voltage Support from Inverter Based Resources 
'''
author: Erik Pohl
Version: 1.0
'''

from PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import matplotlib.pyplot as plt
import scipy.signal as signal
import numpy as np
import math
import statistics as stats

class DynamicVoltageSupport(ControllerAbstract):
    """The controller implements Dynamic Voltage Support for Generator objects as loosely defined in 1547-2018 as "rapid reactive power exchanges during voltage excursions." 
        Subclass of the :class:`PyDSS.pyControllers. pyControllerAbstract.ControllerAbstract` abstract class.

        :param PvObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Generator' element
        :type PvObj: class:`PyDSS.dssElement.dssElement`
        :param Settings: A dictionary that defines the settings for the DynamicVoltageSupport Controller.
        :type Settings: dict
        :param dssInstance: An :class:`opendssdirect` instance
        :type dssInstance: :class:`opendssdirect`
        :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type ElmObjectList: dict
        :param dssSolver: An instance of one of the classed defined in :mod:`PyDSS.SolveMode`.
        :type dssSolver: :mod:`PyDSS.SolveMode`
        :raises: AssertionError if 'PvObj' is not a wrapped OpenDSS Generator element
        :raises: AssertionErrot if 'PvObj' is not a 3ph Generator element

    """
    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(DynamicVoltageSupport, self).__init__(PvObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self._class, self._name = PvObj.GetInfo()
        assert (self._class.lower()=='generator'), 'DynamicVoltageSupport works only with an OpenDSS generator element'
        self.name = "Controller-{}-{}".format(self._class, self._name)
        self._ControlledElm = PvObj
        self.__Settings = Settings
        self.__dssSolver = dssSolver
        self.gen_Phases = float(PvObj.GetParameter('phases'))
        assert(int(self.gen_Phases) == 3), 'DynamicVoltageSupport works only with a 3ph OpenDSS generator element. {ph} ph generator object was used.'.format(
            ph=int(self.gen_Phases)
            )

        # GET GENERATOR ORIGINAL OBJECT PARAMETERS
        # These will be used when resetting the generator behavior in post-fault periods
        self.gen_BaseKV = float(PvObj.GetParameter('kv'))
        self.gen_Srated = float(PvObj.GetParameter('kVA'))
        self.gen_Kw = float(PvObj.GetParameter('kw'))
        self.gen_Kvar = float(PvObj.GetParameter('kvar'))
        self.prev_kvar=self.gen_Kvar
        self.gen_Srated_adjusted=self.gen_Srated
        
        #GET TOML USER-DEFINED SETTINGS
        self.Trv=self.__Settings['Trv'] #time-constant for voltage transducer
        self.dbd1=self.__Settings['dbd1'] #single-sided lower deadband (delta V p.u)
        self.dbd2=self.__Settings['dbd2'] #single-sided upper deadband (delta V p.u)
        self.Kqv=self.__Settings['Kqv'] #proportional gain constant
        self.iqh1=self.__Settings['iqh1'] #current limit for injection (p.u)
        self.iql1=self.__Settings['iql1'] #current limit for absorption (p.u.) --> THIS IS NOT USED
        self.priority=self.__Settings['priority'] #var vs watt priority --> THIS IS NOT USED 
        self.kvarmax_pu=self.__Settings['kvar_max'] #max kvar injection (p.u) (positive number)
        self.kvarmin_pu=self.__Settings['kvar_min'] #max kvar absorption (p.u) (negative number)
        self.post_fault_reset=self.__Settings['post_fault_reset'] #time (s) after fault before gen provides more support
        self.capacitive_support=self.__Settings['capacitive_support'] #bool indicating if gen will provide capacitive support
        self.inductive_support=self.__Settings['inductive_support'] #bool indicating if gen will provide inductive support
        self.current_limited_error_tolerance=self.__Settings['current_limited_error_tolerance'] #error tolerance (%) when evaluating current limit adherance
        self.overvoltage_kva_limited=self.__Settings['overvoltage_kva_limited'] #bool indicating if gen is kva limited
        self.use_with_voltage_ride_through=self.__Settings['Use with Voltage Ride Through'] #bool indicating if DVS controller is used concurrently with VRT controller

        #CALC KVAR LIMITS
        self.kvarmax=self.kvarmax_pu*self.gen_Srated
        self.kvarmin=self.kvarmin_pu*self.gen_Srated

        #RESET GENERATOR MODEL
        self.Model = int(PvObj.SetParameter('model',1)) #set generator model to model 1 to allow for PyDSS-controller current limit
        self.vminpu = float(PvObj.SetParameter('Vminpu',0)) #using arbitrarily wide voltages so that it is always constant kW constant kVAR
        self.vmaxpu = float(PvObj.SetParameter('Vmaxpu',2)) #using arbitrarily wide voltages so that it is always constant kW constant kVAR

        #SET GENERATOR CURRENT LIMITS
        self.gen_imax_per_phase=self.iqh1*(self.gen_Srated/(self.gen_BaseKV*math.sqrt(3)))
        # self.curr_Start=max(self._ControlledElm.GetVariable('CurrentsMagAng')[0:-2:2])

        #SET UP VOLTAGE TRANSDUCER TRANSFER FUNCTION 
        self.V_filter_transfer_function = signal.TransferFunction([1], [self.Trv, 1])
        
        #GET INITIAL CONDITIONS
        self.dt = dssSolver.GetStepResolutionSeconds()
        ave_v_pu = stats.mean(self._ControlledElm.sBus[0].GetVariable("puVmagAngle")[0:-2:2]) #using mean phase voltages
        self.T=[0,self.dt]
        self.V=[ave_v_pu,ave_v_pu]
        self.V_filt=self.V[-1]
        self.Vref=ave_v_pu 
        self.Fault_present=False
        self.fault_reset_start=0
        self.first_step=True

        self.x_out_prev=0
        init_V_filter_transfer_function = signal.TransferFunction([1], [0.1, 1]) #Using a set small time constant for the first step to get up to speed quickly. 
        _,_,init_xout=signal.lsim2(init_V_filter_transfer_function,self.V,self.T,self.x_out_prev)
        self.x_out_prev=init_xout[-1]

        #CALC VOLTAGE DEADBAND FROM THIS INITIAL VREF
        self.upper_db=self.Vref+self.dbd2
        self.lower_db=self.Vref+self.dbd1

        self.kvar_q_mismatch=False
        self.time_advance=False

        return
    
    def Name(self):
        return self.name

    def ControlledElement(self):
        return "{}.{}".format(self._class, self._name)

    def debugInfo(self):
        return 

    def Update(self, Priority, Time, UpdateResults):

        if Priority == 1: 
            #UPDATE TIME ARRAY
            t=self.__dssSolver.GetTotalSeconds()
            if t > self.T[-1]: #Check if this is a new timestep or a second control iteration
                self.time_advance=True
                self.T = np.array([self.T[-1],t])
                self.prev_kvar = float(self._ControlledElm.GetParameter('kvar'))
            else:
                self.time_advance=False
            
            #IF USING DVS WITH VRT WE WILL TRACK GENERATOR STATUS (1.0 = TRIPPED, 0.0 = IN-SERVICE)
            if self.use_with_voltage_ride_through: 
                gen_trip_status=float(self._ControlledElm.GetParameter('Class')) #VRT controller uses opendss 'class' parameter to indicate trip status
            else:
                gen_trip_status=0.0 #if not using with VRT, set trip status to 0.0 (in-service) all the time. 
            
            if not self.use_with_voltage_ride_through or (self.use_with_voltage_ride_through and not bool(gen_trip_status)): 
                
                #COLLECT KEY QUANTITIES
                ave_v_pu = stats.mean(self._ControlledElm.sBus[0].GetVariable("puVmagAngle")[0:-2:2]) 
                p = -1*sum(self._ControlledElm.GetVariable('Powers')[0:-2:2])
                q = -1*sum(self._ControlledElm.GetVariable('Powers')[1:-1:2])
                kvar_setting=float(self._ControlledElm.GetParameter('kvar'))
                kw_setting=float(self._ControlledElm.GetParameter('kw'))

                #CALCULATE FILTERED VOLTAGE USING TRANSFER FUNCTION AT EACH NEW TIMESTEP
                if self.time_advance or self.first_step:
                    self.V=np.array([self.V[-1],ave_v_pu]) #We want this to update in the same priority step, so that any other controllers can impact the voltage first. 
                    _,self.V_filt,xout=signal.lsim2(self.V_filter_transfer_function,self.V,self.T,self.x_out_prev)
                    self.x_out_prev=xout[-1]
                    self.first_step=False
                
                    #CALCULATE V_ERROR
                    V_err=self.V_filt[-1]-self.Vref #positive V_err = overvoltage, negative V_err = undervoltage
            
                if self.time_advance: #IF THERE IS A TIME ADVANCE, REEVALUATE GENERATOR SETTINGS
                    if V_err > self.dbd1 and V_err < self.dbd2: #NO_FAULT CONDITION: if V_err within of user-defined deadband
                        if self.Fault_present: #if transitioning from a faulted state to an unfaulted state, start user-defined reset timer
                            self.fault_reset_start=t
                        self.Fault_present=False
                        self.Vref=self.V_filt[-1] #reset the vref when not in a fault state
                        #reset kw and kvar to original values from the original DSS files. 
                        #Rerun if a second control iteration is needed to get back to original kw and kvar values.
                        #Rerun is needed to avoid transient behavior in sharp transitions. 
                        iter_q=-1*sum(self._ControlledElm.GetVariable('Powers')[1:-1:2])
                        iter_p=-1*sum(self._ControlledElm.GetVariable('Powers')[0:-1:2])
                        error=abs(self.gen_Kw-iter_p)+abs(self.gen_Kvar-iter_q)  #calculate error in iteration p,q compared with original values
                        self._ControlledElm.SetParameter('kw', self.gen_Kw) #set to original p
                        self._ControlledElm.SetParameter('kvar', self.gen_Kvar) #set to original q
                        # return 0 #return 0 if you want these transient behaviors in sharp transitions
                        return error
                    else: #FAULT CONDITION: V_err is outside of user-defined deadband
                        if self.fault_reset_start == 0 or (t-self.fault_reset_start) >= self.post_fault_reset: #check if we have exceeded our reset timer
                            self.Fault_present=True
                            self.fault_reset_start=0
                            if V_err <= self.dbd1: #UNDERVOLTAGE CONDITION
                                if self.capacitive_support: #check if user wants DER to provide capacitive support
                                    if kvar_setting < self.kvarmax: 
                                        new_kvar=kvar_setting+(-V_err*self.Kqv) #calc new kvar value
                                        if new_kvar > self.kvarmax: #if it exceeds user-defined kvarmax
                                            new_kvar=self.kvarmax #set to kvar_max
                                    else:
                                        new_kvar=self.kvarmax
                                else:
                                    new_kvar=self.gen_Kvar #if no capacitive support, keep kvar value as defined in dss files
                                self.gen_Srated_adjusted=self.gen_Srated

                            else: #OVERVOLTAGE 
                                if self.inductive_support:
                                    if kvar_setting > self.kvarmin:
                                        new_kvar=kvar_setting+(-V_err*self.Kqv)
                                        if new_kvar < self.kvarmin:
                                            new_kvar=self.kvarmin
                                    else:
                                        new_kvar=self.kvarmin
                                else:
                                    new_kvar=self.gen_Kvar

                                self.gen_Srated_adjusted=self.gen_Srated
                                # gen_Srated_adjusted=self.gen_Srated*(self.V_filt[-1]) #DER can produce more KVA at higher voltages without exceeding current limit. 
                            if kw_setting==0:
                                new_kw=kw_setting
                            else:
                                new_kw=math.sqrt(((self.gen_Srated_adjusted*self.iqh1)**2)-(new_kvar**2)) #calc new kw value using new kvar and the nameplate rating of gen.

                            self._ControlledElm.SetParameter('kw', new_kw)
                            self._ControlledElm.SetParameter('kvar', new_kvar)
                            return 100 #force another iteration to enforce a current limit when a fault is present and we are altering generator values
                        else: #if we haven't exceeded our reset timer, keep everything the same
                            self.Fault_present=False
                            self.Vref=self.V_filt[-1]#reset Vref to the current timestep voltage
                            iter_q=-1*sum(self._ControlledElm.GetVariable('Powers')[1:-1:2])
                            iter_p=-1*sum(self._ControlledElm.GetVariable('Powers')[0:-1:2])
                            error=abs(self.gen_Kw-iter_p)+abs(self.gen_Kvar-iter_q)
                            self._ControlledElm.SetParameter('kw', self.gen_Kw)
                            self._ControlledElm.SetParameter('kvar', self.gen_Kvar)
                            return error #run a second timestep if needed to get back to original generator values
                    
                else: #RERUNNING TIMESTEP AGAIN AND ENFORCING CURRENT OR KVA LIMIT AT THE CURRENT VOLTAGE LEVEL
                    #GET CURRENT ITERATION KEY QUANTITIES
                    iter_kvar_setting=float(self._ControlledElm.GetParameter('kvar'))
                    iter_kw_setting=float(self._ControlledElm.GetParameter('kw'))
                    iter_curr=max(self._ControlledElm.GetVariable('CurrentsMagAng')[0:-2:2])
                    iter_p=-1*sum(self._ControlledElm.GetVariable('Powers')[0:-1:2])
                    iter_q=-1*sum(self._ControlledElm.GetVariable('Powers')[1:-1:2])
                    iter_v=stats.mean(self._ControlledElm.sBus[0].GetVariable("puVmagAngle")[0:-2:2])*(self.gen_BaseKV)

                    #CALCULATE IF WE OVERSHOT OR UNDERSHOT OUR CURRENT LIMIT AT THE CURRENT VOLTAGE LEVEL
                    curr_over_under=iter_curr-self.gen_imax_per_phase
                    curr_over_under_pct=curr_over_under/self.gen_imax_per_phase

                    #CALCULATE IF WE OVERSHOT OUR GENERATOR KVA NAMEPLATE
                    kva_overshoot=(math.sqrt((iter_p**2)+(iter_q**2)))-self.gen_Srated
                    kva_overshoot_pct=kva_overshoot/self.gen_Srated

                    #READJUST QUANTITIES AS NEEDED
                    if self.Fault_present: #Only adjust quantities if there is a fault present and we are changing generator behavior
                        if self.overvoltage_kva_limited and kva_overshoot_pct>self.current_limited_error_tolerance: #if user wants to enforce a kva limit and we have exceeded that
                            if self.priority.lower() == 'var': #model currently assumes always VAr priority
                                if iter_kw_setting>0:# if there active power generation
                                    new_kw=math.sqrt((self.gen_Srated_adjusted**2)-(iter_kvar_setting**2))#calc new kw setting based on current kvar setting
                                    if new_kw>0: #if the new kw settings does not cause kw to go negative
                                        self._ControlledElm.SetParameter('kw', new_kw)
                                        self._ControlledElm.SetParameter('kvar', iter_kvar_setting)
                                    else: #otherwise just set kw to 0
                                        self._ControlledElm.SetParameter('kw', 0)
                                        self._ControlledElm.SetParameter('kvar', iter_kvar_setting)
                                else: #if kw setting is already 0
                                    new_kvar=math.sqrt((self.gen_Srated_adjusted**2)-(iter_kw_setting**2))
                                    self._ControlledElm.SetParameter('kw', iter_kw_setting) #no need to calculate a new kW setting
                                    self._ControlledElm.SetParameter('kvar', new_kvar)
                            return kva_overshoot_pct #force a rerun to ensure we adhere to current and kva limit
                        
                        else: #if we haven't exceeded our kva limit, check if we have exceeded our current limit
                            if abs(curr_over_under_pct)>self.current_limited_error_tolerance:
                                if self.overvoltage_kva_limited and curr_over_under_pct<0:# if the DER is being kva limited, we allow for DER to undershoot its current limit
                                    return 0
                                else: #if it is not kva limited, then we will enfore only the current limit
                                    new_kva=self.gen_imax_per_phase*(iter_v*math.sqrt(3))
                                    if self.priority.lower() == 'var': #it is always var priority in this model
                                        if iter_kw_setting>0: # if there active power generation
                                            new_kw=math.sqrt((new_kva**2)-(iter_kvar_setting**2))#calc new kw setting based on current kvar setting
                                            if new_kw>0: #if the new kw settings does not cause kw to go negative
                                                self._ControlledElm.SetParameter('kw', new_kw)
                                                self._ControlledElm.SetParameter('kvar', iter_kvar_setting)
                                            else: #otherwise just set kw to 0
                                                self._ControlledElm.SetParameter('kw', 0)
                                                self._ControlledElm.SetParameter('kvar', iter_kvar_setting)
                                        else: #if kw setting is already 0
                                            new_kvar=math.sqrt((new_kva**2)-(iter_kw_setting**2))
                                            self._ControlledElm.SetParameter('kw', iter_kw_setting) #no need to calculate a new kW setting
                                            self._ControlledElm.SetParameter('kvar', new_kvar)
                                    return abs(curr_over_under_pct) #force a rerun to ensure we adhere to current and kva limit
                    else:
                        return 0
                return 0
            else: #if the generator is in a tripped state (when using with VRT controller) then keep kw and kvar at 0
                self._ControlledElm.SetParameter('kw', 0)
                self._ControlledElm.SetParameter('kvar', 0)
                return 0
        return 0 


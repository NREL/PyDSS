#Algebraic model for Type D motor - residential air conditioner

import scipy.signal as signal
import numpy as np
import math

from pydss.pyControllers.models import MotorStallSettings
from pydss.pyControllers.pyControllerAbstract import ControllerAbstract

class MotorStall(ControllerAbstract):   
    def __init__(self, motor_obj, settings, dss_instance, elm_object_list, dss_solver):
        super(MotorStall, self).__init__(motor_obj, settings, dss_instance, elm_object_list, dss_solver)

        self._class, self._name = motor_obj.GetInfo()
        assert self._class == "Load", "Motor stall model can only be used with load models"
        assert motor_obj.NumPhases == 1, "Motor stall model can only be used with single phase loads"
        
        self.name = "Controller-{}-{}".format(self._class, self._name)
        self._controlled_element = motor_obj
        self._settings = MotorStallSettings(**settings)
        self._dss_solver = dss_solver
        self.mode = 3
        self.model_mode = self._controlled_element.SetParameter('model', self.mode) # 3 - motor, 1 - Standard constant P+jQ
        self._controlled_element.SetParameter('vminpu', 0.0)

        self.kw_rated = self._controlled_element.GetParameter('kw')
        self.kvar_rated = self._controlled_element.GetParameter('kvar')
        self.kva_rated = (self.kw_rated**2 + self.kvar_rated**2)**0.5
            
        self.stall_time_start = 0
        self.stall = False

        self.r_stall_pu = self._settings.r_stall_pu
        self.va_base = 100 * 1e6
        self.kvbase = self._controlled_element.sBus[0].GetVariable("kVBase")
        self.i_base = 1e3 * self.kw_rated / 1e3 * self.kvbase

        self.dt = dss_solver.GetStepResolutionSeconds()
        self.h = signal.TransferFunction([1], [self._settings.t_th, 1])
        self.r = signal.TransferFunction([1], [self._settings.t_restart, 1])
        
        self.u = [0, 0]
        self.t_arr = [0, self.dt]
        self.x = 0
        
        self.i2r = 0
        
        self.p_stall = 0
        self.q_stall = 0
        
        return
    
    def Name(self):
        return self.name

    def ControlledElement(self):
        return "{}.{}".format(self._class, self._name)

    def debugInfo(self):
        return 

    def Update(self, Priority, time, update_results):
        self.t = self._dss_solver.GetTotalSeconds()
        if self.i_base:    
            self.current_pu = self._controlled_element.GetVariable('CurrentsMagAng')[0] / self.i_base
            self.voltage = self._controlled_element.GetVariable('VoltagesMagAng')[0]
            self.p = self._controlled_element.GetVariable('Powers')[0]
            self.q = self._controlled_element.GetVariable('Powers')[1]
            self.voltage_pu = self._controlled_element.sBus[0].GetVariable("puVmagAngle")[0]

            if Priority == 0:
                
                i2r = self.current_pu ** 2 * self.r_stall_pu       
                self.i2r = max(self.i2r, i2r)  
                self.t = np.array([self.t_arr [-1], self.t])
                self.u = np.array([self.u[-1], self.i2r])
                tout, yout, xout = signal.lsim(self.h, self.u, self.t_arr, self.x)
                self.x = xout[-1]
                i2r_calc = yout[-1] / 50.0
                
            
                comp_lf = self.p / self.kw_rated
                comp_pf = 0.75 #self.p / (self.p**2 + self.q**2)**0.5
                
                v_stall_adj = self._settings.v_stall*(1 + self._settings.lf_adj * (comp_lf-1))
                v_break_adj = self._settings.v_break*(1 + self._settings.lf_adj * (comp_lf-1))
                
                p0 = 1 - self._settings.k_p1 * (1-v_break_adj)**self._settings.n_p1
                q0 = ((1 - comp_pf**2)**0.5 / comp_pf)-self._settings.k_q1*(1-v_break_adj)**self._settings.n_q1
                
                p = self.p / self.kw_rated
                q = self.q / self.kvar_rated
                
                if self.voltage_pu > v_break_adj and not self.stall: 
                    p = p0 + self._settings.k_p1*(self.voltage_pu-v_break_adj)**self._settings.n_p1
                    q = q0 + self._settings.k_q1*(self.voltage_pu-v_break_adj)**self._settings.n_q1
                    self._controlled_element.SetParameter('kw', self.kw_rated * p) 
                    self._controlled_element.SetParameter('kvar', self.kvar_rated * q) 

                elif self.voltage_pu <= v_break_adj and not self.stall:   
                    p = p0 + self._settings.k_p2 * (v_break_adj - self.voltage_pu)**self._settings.n_p2
                    q = q0 + self._settings.k_q2 * (v_break_adj - self.voltage_pu)**self._settings.n_q2
                    
                    self._controlled_element.SetParameter('kw', self.kw_rated * p ) 
                    self._controlled_element.SetParameter('kvar', self.kvar_rated * q) 

                    if self.voltage_pu < v_stall_adj and not self.stall:
                        self.p_stall = self._controlled_element.GetParameter('kw')
                        self.q_stall = self._controlled_element.GetParameter('kvar')
                        self.stall_time_start = self._dss_solver.GetTotalSeconds()
                        self.stall = True
                
                if self.voltage_pu > v_stall_adj and self.stall:
                    self.stall_time = self._dss_solver.GetTotalSeconds() - self.stall_time_start
                    if self.stall_time < self._settings.t_stall:
                        self._controlled_element.SetParameter('kw', self.p_stall)
                        self._controlled_element.SetParameter('kvar', self.q_stall)
                    else:
                        if i2r_calc < self._settings.t_th1t:
                            Kth = 1
                        elif i2r_calc > self._settings.t_th2t:
                            Kth = 0
                        else:
                            m = 1 / (self._settings.t_th1t - self._settings.t_th2t)
                            c = - m * self._settings.t_th2t
                            Kth = m * i2r_calc + c

                        self._controlled_element.SetParameter('kw',  self.p_stall * Kth ) 
                        self._controlled_element.SetParameter('kvar', self.q_stall * Kth ) 
    
            self.model_mode_old = self.model_mode
        
        return 0


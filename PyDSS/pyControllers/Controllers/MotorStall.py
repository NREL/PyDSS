#Algebraic model for Type D motor - Residential air conditioner
'''
author: Kapil Duwadi
Version: 1.0
'''

from PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import matplotlib.pyplot as plt
import scipy.signal as signal
import numpy as np
import random
import math
import os

class MotorStall(ControllerAbstract):
    """The controller locks a regulator in the event of reverse power flow. Subclass of the :class:`PyDSS.pyControllers.
    pyControllerAbstract.ControllerAbstract` abstract class.

        :param RegulatorObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Regulator' element
        :type FaultObj: class:`PyDSS.dssElement.dssElement`
        :param Settings: A dictionary that defines the settings for the PvController.
        :type Settings: dict
        :param dssInstance: An :class:`opendssdirect` instance
        :type dssInstance: :class:`opendssdirect`
        :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type ElmObjectList: dict
        :param dssSolver: An instance of one of the classed defined in :mod:`PyDSS.SolveMode`.
        :type dssSolver: :mod:`PyDSS.SolveMode`
        :raises: AssertionError if 'RegulatorObj' is not a wrapped OpenDSS Regulator element

    """
        
    def __init__(self, MotorObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(MotorStall, self).__init__(MotorObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self._class, self._name = MotorObj.GetInfo()
        assert self._class == "Load", "Motor stall model can only be used with load models"
        assert MotorObj.NumPhases == 1, "Motor stall model can only be used with single phase loads"
        
        self.name = "Controller-{}-{}".format(self._class, self._name)
        self._ControlledElm = MotorObj
        self.__Settings = Settings
        self.__dssSolver = dssSolver
        self.mode = 3
        self.model_mode = self._ControlledElm.SetParameter('model', self.mode) # 3 - motor, 1 - Standard constant P+jQ
        self._ControlledElm.SetParameter('vminpu', 0.0)

        self.kw = self.__Settings['ratedKW']
        S = self.kw / self.__Settings['ratedPF']
        self.kvar = math.sqrt(S**2 - self.kw**2)
        mode = 2
        
        if mode == 1:
            self.kw_rated = self._ControlledElm.SetParameter('kw', self.kw)
            self.kvar_rated = self._ControlledElm.SetParameter('kvar', self.kvar)        
        elif mode == 2:
            self.kw_rated = self._ControlledElm.GetParameter('kw')
            self.kvar_rated = self._ControlledElm.GetParameter('kvar')
        self.kva_rated = (self.kw_rated**2 + self.kvar_rated**2)**0.5
            
        self.stall_time_start = 0
        self.stall = False
        self.disconnected =False
        self.Tdisconnect_start = 0
        
        self.R_stall_pu = self.__Settings['R_stall_pu']
        self.va_base = 100 * 1e6
        self.kvbase = self._ControlledElm.sBus[0].GetVariable("kVBase")
        self.Ibase = 1e3 * self.kw_rated / 1e3 * self.kvbase

        self.dt = dssSolver.GetStepResolutionSeconds()
        self.H = signal.TransferFunction([1], [self.__Settings['Tth'], 1])
        self.R = signal.TransferFunction([1], [self.__Settings['Trestart'], 1])
        
        self.U = [0, 0]
        self.T = [0, self.dt]
        self.X = 0

        self.rU = [0, 0]
        self.rT = [0, self.dt]
        self.rX = 0
        self.v = 0
    
        self._peak = 0
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

    def Update(self, Priority, Time, UpdateResults):
        self.t = self.__dssSolver.GetTotalSeconds()
        if self.Ibase:    
            self.current_pu = self._ControlledElm.GetVariable('CurrentsMagAng')[0] / self.Ibase
            self.voltage = self._ControlledElm.GetVariable('VoltagesMagAng')[0]
            self.p = self._ControlledElm.GetVariable('Powers')[0]
            self.q = self._ControlledElm.GetVariable('Powers')[1]
            self.voltage_pu = self._ControlledElm.sBus[0].GetVariable("puVmagAngle")[0]

            if Priority == 0:
                
                i2r = self.current_pu ** 2 * self.R_stall_pu       
                self.i2r = max(self.i2r, i2r)  
                self.T = np.array([self.T[-1], self.t])
                self.U = np.array([self.U[-1], self.i2r])
                tout, yout, xout = signal.lsim2(self.H, self.U, self.T, self.X)
                self.X = xout[-1]
                i2r_calc = yout[-1] / 50.0
                
            
                CompLF = self.p / self.kw_rated
                CompPF = 0.75 #self.p / (self.p**2 + self.q**2)**0.5
                
                V_stall_adj = self.__Settings['Vstall']*(1 + self.__Settings['LFadj'] * (CompLF-1))
                V_break_adj = self.__Settings['Vbreak']*(1 + self.__Settings['LFadj'] * (CompLF-1))
                
                P0 = 1 - self.__Settings['Kp1'] * (1-V_break_adj)**self.__Settings['Np1']
                Q0 = ((1 - CompPF**2)**0.5 / CompPF)-self.__Settings['Kq1']*(1-V_break_adj)**self.__Settings['Nq1']
                
                p = self.p / self.kw_rated
                q = self.q / self.kvar_rated
                
                if self.voltage_pu > V_break_adj and not self.stall: 
                    p = P0 + self.__Settings['Kp1']*(self.voltage_pu-V_break_adj)**self.__Settings['Np1']
                    q = Q0 + self.__Settings['Kq1']*(self.voltage_pu-V_break_adj)**self.__Settings['Nq1']
                    self._ControlledElm.SetParameter('kw', self.kw_rated * p) 
                    self._ControlledElm.SetParameter('kvar', self.kvar_rated * q) 

                elif self.voltage_pu <= V_break_adj and not self.stall:   
                    p = P0 + self.__Settings['Kp2'] * (V_break_adj - self.voltage_pu)**self.__Settings['Np2']
                    q = Q0 + self.__Settings['Kq2'] * (V_break_adj - self.voltage_pu)**self.__Settings['Nq2']
                    
                    self._ControlledElm.SetParameter('kw', self.kw_rated * p ) 
                    self._ControlledElm.SetParameter('kvar', self.kvar_rated * q) 

                    if self.voltage_pu < V_stall_adj and not self.stall:
                        self.p_stall = self._ControlledElm.GetParameter('kw')
                        self.q_stall = self._ControlledElm.GetParameter('kvar')
                        self.stall_time_start = self.__dssSolver.GetTotalSeconds()
                        self.stall = True
                
                if self.voltage_pu > V_stall_adj and self.stall:
                    self.stall_time = self.__dssSolver.GetTotalSeconds() - self.stall_time_start
                    if self.stall_time < self.__Settings['Tstall']:
                        self._ControlledElm.SetParameter('kw', self.p_stall)
                        self._ControlledElm.SetParameter('kvar', self.q_stall)
                    else:
                        if i2r_calc < self.__Settings['Tth1t']:
                            Kth = 1
                        elif i2r_calc > self.__Settings['Tth2t']:
                            Kth = 0
                        else:
                            m = 1 / (self.__Settings['Tth1t'] - self.__Settings['Tth2t'])
                            c = - m * self.__Settings['Tth2t']
                            Kth = m * i2r_calc + c

                        self._ControlledElm.SetParameter('kw',  self.p_stall * Kth ) 
                        self._ControlledElm.SetParameter('kvar', self.q_stall * Kth ) 
    
            self.model_mode_old = self.model_mode
        
        return 0


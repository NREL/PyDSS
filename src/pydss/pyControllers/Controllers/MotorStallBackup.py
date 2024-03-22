#Algebraic model for Type D motor - Residential air conditioner
'''
author: Kapil Duwadi
Version: 1.0
'''

from pydss.pyControllers.pyControllerAbstract import ControllerAbstract
import matplotlib.pyplot as plt
import scipy.signal as signal
import numpy as np
import random
import math
import os

class MotorStallBackup(ControllerAbstract):
    """The controller locks a regulator in the event of reverse power flow. Subclass of the :class:`pydss.pyControllers.
    pyControllerAbstract.ControllerAbstract` abstract class.

        :param RegulatorObj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'Regulator' element
        :type FaultObj: class:`pydss.dssElement.dssElement`
        :param Settings: A dictionary that defines the settings for the PvController.
        :type Settings: dict
        :param dssInstance: An :class:`opendssdirect` instance
        :type dssInstance: :class:`opendssdirect`
        :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type ElmObjectList: dict
        :param dssSolver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
        :type dssSolver: :mod:`pydss.SolveMode`
        :raises: AssertionError if 'RegulatorObj' is not a wrapped OpenDSS Regulator element

    """
        
    def __init__(self, MotorObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(MotorStallBackup, self).__init__(MotorObj, Settings, dssInstance, ElmObjectList, dssSolver)
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
        self.kvbase = self._ControlledElm.sBus[0].GetVariable("kVBase")
        self.Ibase = 1e3 * self.kva_rated /1e3 * self.kvbase

        self.dt = dssSolver.GetStepResolutionSeconds()
        self.H = signal.TransferFunction([1], [self.__Settings['Tth'], 1])
        self.R = signal.TransferFunction([1], [self.__Settings['Trestart'], 1])
        
        self.U = [35.029919199211, 35.029919199211]
        self.T = [0, self.dt]
        self.X = 0

        self.rU = [0, 0]
        self.rT = [0, self.dt]
        self.rX = 0
        self.v = 0
        
        self.voltage_pu_old = 1.0
        # Delete after debug #
        
        self.file = open(r"C:\Users\alatif\Desktop\NAERM\models\17735\motor.csv", "w")
        self.file.write("CompLF,CompPF,V_stall_adj,V_break_adj,P0,Q0,p_run_pu,q_run_pu,p_stall_pu,q_stall_pu\n")
        
        return
    
    def Name(self):
        return self.name

    def ControlledElement(self):
        return "{}.{}".format(self._class, self._name)

    def debugInfo(self):
        return 

    def Update(self, Priority, Time, UpdateResults):
        
        self.t = self.__dssSolver.GetTotalSeconds()
        self.current_pu = self._ControlledElm.GetVariable('CurrentsMagAng')[0] / self.Ibase
        self.voltage = self._ControlledElm.GetVariable('VoltagesMagAng')[0]
        self.p = self._ControlledElm.GetVariable('Powers')[0]
        self.q = self._ControlledElm.GetVariable('Powers')[1]
        self.voltage_pu = self._ControlledElm.sBus[0].GetVariable("puVmagAngle")[0]

        if Priority == 0:
            
            u = self.current_pu ** 2 * self.R_stall_pu       
          
            CompLF = 1.0 #self.p / self.kw_rated
            CompPF = self.p / (self.p**2 + self.q**2)**0.5
            
            V_stall_adj = self.__Settings['Vstall']*(1 + self.__Settings['LFadj'] * (CompLF-1))
            V_break_adj = self.__Settings['Vbreak']*(1 + self.__Settings['LFadj'] * (CompLF-1))
            
            P0 = 1 - self.__Settings['Kp1'] * (1-V_break_adj)**self.__Settings['Np1']
            Q0 = ((1 - CompPF**2)**0.5 / CompPF)-self.__Settings['Kq1']*(1-V_break_adj)**self.__Settings['Nq1']
            
            
            p_run_pu = P0 + self.__Settings['Kp1']*(self.voltage_pu-V_break_adj)**self.__Settings['Np1']
            q_run_pu = Q0 + self.__Settings['Kq1']*(self.voltage_pu-V_break_adj)**self.__Settings['Nq1']
            
            p_stall_pu = P0 + self.__Settings['Kp2'] * (V_break_adj - self.voltage_pu)**self.__Settings['Np2']
            q_stall_pu = Q0 + self.__Settings['Kq2'] * (V_break_adj - self.voltage_pu)**self.__Settings['Nq2']

            self.file.write(f"{CompLF},{CompPF},{V_stall_adj},{V_break_adj},{P0},{Q0},{p_run_pu},{q_run_pu},{p_stall_pu},{q_stall_pu}\n")
            self.file.flush()

            if self.voltage_pu < V_stall_adj and self.stall and self.model_mode == self.mode:
                self.stall_time = self.__dssSolver.GetTotalSeconds() - self.stall_time_start
                if self.stall_time > self.__Settings['Tstall']:
                    self._ControlledElm.SetParameter('kw', self.kw_rated * self.__Settings['Pfault'])
                    self._ControlledElm.SetParameter('kvar', self.kvar_rated * self.__Settings['Qfault'])
                    self.model_mode = self._ControlledElm.SetParameter('model', 2)
                      
            if self.voltage_pu < V_stall_adj and not self.stall:
                self.stall_time_start = self.__dssSolver.GetTotalSeconds()
                self.stall = True
            
            u = 1 if self.model_mode == 2 else 0
            
            self.T = np.array([self.T[-1], self.t])
            self.U = np.array([self.U[-1], u])
            tout, yout, xout = signal.lsim(self.H, self.U, self.T, self.X)
            self.X = xout[-1]
            theeta = yout[-1]
            
            if theeta < self.__Settings['Tth1t']:
                Kth = 1
            elif theeta > self.__Settings['Tth2t']:
                Kth = 0
            else:
                m = 1 / (self.__Settings['Tth1t'] - self.__Settings['Tth2t'])
                c = - m * self.__Settings['Tth2t']
                Kth = m * theeta + c
            
            if self.model_mode == 2:
                p_stall = self.kw_rated * self.__Settings['Pfault'] 
                q_stall = self.kvar_rated * self.__Settings['Qfault'] 
                
                
                if p_stall * Kth > self.kw_rated:
                    self._ControlledElm.SetParameter('kw', p_stall * Kth)
                else:
                    self._ControlledElm.SetParameter('kw', self.kw_rated * p_run_pu)
                
                #TODO: uncommect the line below and comment the if statements below to allow q to fall below self.kvar_rated
                #self._ControlledElm.SetParameter('kvar', q_stall * Kth) 
                
                if q_stall * Kth > self.kvar_rated:
                    self._ControlledElm.SetParameter('kvar', self.p * Kth)
                else:
                    self._ControlledElm.SetParameter('kvar', self.kvar_rated* q_run_pu)

            if Kth==0 and self.voltage_pu > self.__Settings['Vrstrt']:
                self.v = 1
                
            self.rT = np.array([self.rT[-1], self.t])
            self.rU = np.array([self.rU[-1], self.v])
            _, yout_r, xout_r = signal.lsim(self.R, self.rU, self.rT, self.rX)
            self.rX = xout_r[-1]
            reconnect = yout_r[-1]

            set_p =  self._ControlledElm.GetParameter("kw")
            set_q =  self._ControlledElm.GetParameter("kvar")

            if set_p == self.kw_rated and set_q== self.kvar_rated and self.stall and reconnect>0:
                self.model_mode = self._ControlledElm.SetParameter('model', self.mode)
                self.stall = False
                
            self.voltage_pu_old = self.voltage_pu
        self.model_mode_old = self.model_mode
        return 0


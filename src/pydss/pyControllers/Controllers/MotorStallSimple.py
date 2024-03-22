#Algebraic model for Type D motor - Residential air conditioner
'''
author: Aadil Latif
Version: 1.0
'''

from pydss.pyControllers.pyControllerAbstract import ControllerAbstract
from pydss.pyControllers.models import MotorStallSimpleSettings

class MotorStallSimple(ControllerAbstract):

    def __init__(self, motor_obj, settings, dss_instance, elm_object_list, dss_solver):
        super(MotorStallSimple, self).__init__(motor_obj, settings, dss_instance, elm_object_list, dss_solver)
        self._class, self._name = motor_obj.GetInfo()
        self.name = "Controller-{}-{}".format(self._class, self._name)
        self._controlled_element = motor_obj
        self._settings = MotorStallSimpleSettings(**settings)
        self._dss_solver = dss_solver

        self._controlled_element.SetParameter('model', 3)
        self._controlled_element.SetParameter('vminpu', 0.0)
        self._controlled_element.SetParameter('vlowpu', 0.0)
        self.kw = self._controlled_element.GetParameter('kw')
        self.kvar = self._controlled_element.GetParameter('kvar')

        self.stall_time_start = 0
        self.stall = False
        self.disconnected =False
        self.t_disconnect_start = 0
        
        return


    def Name(self):
        return self.name

    def ControlledElement(self):
        return "{}.{}".format(self._class, self._name)

    def debugInfo(self):
        return [] #[self._settings['Control{}'.format(i+1)] for i in range(3)]


    def Update(self, priority, time, _):
        assert priority in [0, 1, 2], "Valid control priorities can range from 0-2."
        v_e_mags = 1.0
        if priority == 0:
            v_base = self._controlled_element.sBus[0].GetVariable('kVBase') * 1000
            v_e_mags = max(self._controlled_element.GetVariable('VoltagesMagAng')[::2])/ v_base
            if v_e_mags < self._settings.v_stall and not self.stall and not self.disconnected:                
                self._controlled_element.SetParameter('kw', self.kw * self._settings.p_fault)
                self._controlled_element.SetParameter('kvar', self.kvar * self._settings.q_fault )
                self._controlled_element.SetParameter('model', 2)
                self.stall = True
                self.stall_time_start = self._dss_solver.GetTotalSeconds()
                return 0.1
            return 0
        if priority == 1:
            if self.stall:
                
                self.stall_time = self._dss_solver.GetTotalSeconds() - self.stall_time_start
                if self.stall_time > self._settings.t_protection:
                    self.stall = False
                    self.disconnected = True
                    self._controlled_element.SetParameter('kw', 0)
                    self._controlled_element.SetParameter('kvar', 0)
                    self.t_disconnect_start = self._dss_solver.GetTotalSeconds()
                return 0 
            return 0
        if priority == 2:
            if self.disconnected:
                time = self._dss_solver.GetTotalSeconds() - self.t_disconnect_start
                if time > self._settings.t_reconnect and v_e_mags > self._settings.v_stall:
                    self.disconnected = False
                    self._controlled_element.SetParameter('kw', self.kw)
                    self._controlled_element.SetParameter('kvar', self.kvar)
                    self._controlled_element.SetParameter('model', 3)
                    self._controlled_element.SetParameter('vminpu', 0.0)
        return 0


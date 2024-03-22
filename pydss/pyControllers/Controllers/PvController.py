from collections import namedtuple
import math

from pydss.pyControllers.enumerations import SmartControls, ControlPriority, VoltWattCurtailmentStrategy, VoltageCalcModes
from pydss.pyControllers.pyControllerAbstract import ControllerAbstract
from pydss.pyControllers.models import PvControllerModel


class PvController(ControllerAbstract):
    """Implementation of smart control modes of modern inverter systems. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

        :param pv_obj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'PVSystem' element
        :type FaultObj: class:`pydss.dssElement.dssElement`
        :param settings: A dictionary that defines the settings for the PvController.
        :type settings: dict
        :param dss_instance: An :class:`opendssdirect` instance
        :type dss_instance: :class:`opendssdirect`
        :param element_object_list: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type element_object_list: dict
        :param dss_solver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
        :type dss_solver: :mod:`pydss.SolveMode`
        :raises: Assertionerror if 'pv_obj' is not a wrapped OpenDSS PVSystem element

    """

    def __init__(self, pv_obj, settings, dss_instance, element_object_list, dss_solver):
        """Constructor method
        """
        
        super(PvController, self).__init__(pv_obj, settings, dss_instance, element_object_list, dss_solver)
        self.time_change = False
        self.time = (-1, 0)
        self.old_q_pv = 0
        self.old_p_calc = 0

        self._v_disconnected = False
        self._p_disconnected = False

        self._element_object_list = element_object_list
        self.control_dict = {
            SmartControls.NONE : lambda: 0,
            SmartControls.CONSTANT_POWER_FACTOR : self.constant_powerfactor_control,
            SmartControls.VARIABLE_POWER_FACTOR : self.variable_powerfactor_control,
            SmartControls.VOLT_VAR : self.volt_var_control,
            SmartControls.VOLT_WATT : self.volt_watt_control,
            SmartControls.TRIP : self.cutoff_control,
        }

        self._controlled_element = pv_obj
        self.ce_class, self.ce_name = self._controlled_element.GetInfo()

        assert (self.ce_class.lower()=='pvsystem'), 'PvController works only with an OpenDSS PVSystem element'
        self._name = 'pyCont_' + self.ce_class + '_' +  self.ce_name
        if '_' in  self.ce_name:
            self.phase =  self.ce_name.split('_')[1]
        else:
            self.phase = None
        self._element_object_list = element_object_list
        self._controlled_element = pv_obj
        self._dss_instance = dss_instance
        self._dss_solver = dss_solver
        self._settings = PvControllerModel(**settings)

        self._base_kv = float(pv_obj.GetParameter('kv'))
        self._s_rated = float(pv_obj.GetParameter('kVA'))
        self._p_rated = float(pv_obj.GetParameter('Pmpp'))
        self._q_rated = float(pv_obj.GetParameter('kvarMax'))
        self._cutin = float(pv_obj.SetParameter('%cutin', 0)) / 100
        self._cutout = float(pv_obj.SetParameter('%cutout', 0)) / 100
        self._damp_coef = self._settings.damp_coef
        self._pf_rated = self._settings.pf_lim
        self.p_mppt = 100
        self.pf = 1

        self.update = []
            
        for i in range(1, 4):
            controller_type = getattr(self._settings, 'control' + str(i))
            self.update.append(self.control_dict[controller_type])


        if self._settings.priority == ControlPriority.VAR:
            pv_obj.SetParameter('Wattpriority', "False")
        elif self._settings.priority == ControlPriority.WATT:
            pv_obj.SetParameter('Wattpriority', "True")
        #pv_obj.SetParameter('VarFollowInverter', "False")

        #self.q_lim_pu = self._q_rated / self._s_rated if self._q_rated < self._s_rated else 1

        self.q_lim_pu = min(self._q_rated / self._s_rated, self._settings.q_lim_pu, 1.0)
        self.itr = 0
        return

    def Name(self):
        return self._name

    def ControlledElement(self):
        return "{}.{}".format(self.ce_class, self.ce_name)

    def debugInfo(self):
        return [getattr(self._settings, 'control' + str(i)) for i in range(3)]

    def Update(self, priority, time, update):
        self.time_change = self.time != (priority, time)
        self.time = (priority, time)
        p_pv = -sum(self._controlled_element.GetVariable('Powers')[::2]) / self._p_rated

        if self.time_change:
            self.itr = 0
        else:
            self.itr += 1

        if self._p_disconnected:
            if p_pv < self._cutin:
                return 0
            else:
                self._p_disconnected = False
        else:
            if p_pv < self._cutout:
                self._p_disconnected = True
                self._controlled_element.SetParameter('pf', 1)
                return 0
        return self.update[priority]()

    def volt_watt_control(self):
        """Volt / Watt  control implementation
        """
        u_min_c = self._settings.u_min_c
        u_max_c = self._settings.u_max_c
        p_min  = self._settings.p_min_vw / 100

        u_in = max(self._controlled_element.sBus[0].GetVariable('puVmagAngle')[::2])
        p_pv = -sum(self._controlled_element.GetVariable('Powers')[::2]) / self._s_rated
        q_pv = -sum(self._controlled_element.GetVariable('Powers')[1::2]) / self._s_rated


        #p_pvoutPU = p_pv / self._p_rated

        p_lim = (1 - q_pv ** 2) ** 0.5 if self._settings.vw_type == VoltWattCurtailmentStrategy.AVAILABLE_POWER else 1
        m = (1 - p_min) / (u_min_c - u_max_c)
        #m = (p_lim - p_min) / (u_min_c - u_max_c)
        c = ((p_min * u_min_c) - u_max_c) / (u_min_c - u_max_c)

        if u_in < u_min_c:
            p_calc = p_lim
        elif u_in < u_max_c and u_in > u_min_c:
            p_calc = min(m * u_in + c, p_lim)
        else:
            p_calc = p_min

        if p_pv > p_calc or (p_pv > 0 and self.p_mppt < 100):
            # adding heavy ball term to improve convergence
            dp = (p_pv - p_calc) * 0.5 / self._damp_coef + (self.old_p_calc - p_pv) * 0.1 / self._damp_coef
            p_calc = p_pv - dp
            self.p_mppt = min(self.p_mppt * p_calc / p_pv, 100)
            self._controlled_element.SetParameter('%Pmpp', self.p_mppt)
            self.pf = math.cos(math.atan(q_pv / p_calc))
            if q_pv < 0:
                self.pf = -self.pf
            self._controlled_element.SetParameter('pf', self.pf)
        else:
            dp = 0

        error = abs(dp)
        self.old_p_calc = p_pv
        return error

    def cutoff_control(self):
        """Over voltage trip implementation
        """
        u_in = max(self._controlled_element.sBus[0].GetVariable('puVmagAngle')[::2])
        u_cut = self._settings['%u_cutoff']
        if u_in >= u_cut:
            self._controlled_element.SetParameter('%Pmpp', 0)
            self._controlled_element.SetParameter('pf', 1)
            if self._v_disconnected:
                return 0
            else:
                self._v_disconnected = True
                return self._p_rated

        if self.time_change and self._v_disconnected and u_in < u_cut:
            self._controlled_element.SetParameter('%Pmpp', self.p_mppt)
            self._controlled_element.SetParameter('pf', self.pf)
            self._v_disconnected = False
            return self._p_rated

        return 0

    def constant_powerfactor_control(self):
        """Constant power factor implementation
        """
        pf_set = self._settings.pf
        pf_act = self._controlled_element.GetParameter('pf')
        p_pv = abs(sum(self._controlled_element.GetVariable('Powers')[::2])) / self._s_rated
        q_pv = -sum(self._controlled_element.GetVariable('Powers')[1::2]) / self._s_rated

        if self._settings.priority == ControlPriority.PF:
           # if self.time_change:
            p_lim = pf_set * 100
            self._controlled_element.SetParameter('%Pmpp', p_lim)
           # else:
        else:
            if self._settings.priority == ControlPriority.VAR:
                #add code for var priority here
                p_lim = 0
            else:
                p_lim = 1
            if self.time_change:
                self.p_mppt = 100
            else:
                self.p_mppt = p_lim  * self._s_rated

        error = abs(pf_set + pf_act)
        self._controlled_element.SetParameter('pf', str(-pf_set))
        return error

    def variable_powerfactor_control(self):
        """Variable power factor control implementation
        """
        p_min = self._settings.p_min
        p_max = self._settings.p_max
        pf_min = self._settings.pf_min
        pf_max = self._settings.pf_max
        self._dss_solver.reSolve()
        p_calc = abs(sum(-(float(x)) for x in self._controlled_element.GetVariable('Powers')[0::2]) ) / self._s_rated
        if p_calc > 0:
            if p_calc < p_min:
                pf = pf_max
            elif p_calc > p_max:
                pf = pf_min
            else:
                m = (pf_max - pf_min) / (p_min - p_max)
                c = (pf_min * p_min - pf_max * p_max) / (p_min - p_max)
                pf = p_calc * m + c
        else:
            pf = pf_max

        self._controlled_element.SetParameter('irradiance', 1)
        self._controlled_element.SetParameter('pf', str(-pf))
        self._dss_solver.reSolve()

        for i in range(10):
            error = pf + float(self._controlled_element.GetParameter('pf'))
            if abs(error) < 1E-4:
                break
            p_irr = float(self._controlled_element.GetParameter('irradiance'))
            self._controlled_element.SetParameter('pf', str(-pf))
            self._controlled_element.SetParameter('irradiance', p_irr * (1 + error*1.5))
            self._dss_solver.reSolve()

        return 0

    def volt_var_control(self):
        """Volt / var control implementation
        """

        u_mag = self._controlled_element.GetVariable('VoltagesMagAng')[::2]
        u_mag = [i for i in u_mag if i != 0]
        kv_base = self._controlled_element.sBus[0].GetVariable('kVBase') * 1000

        if self._settings.voltage_calc_mode == VoltageCalcModes.MAX:
            u_in = max(u_mag) / kv_base
        elif self._settings.voltage_calc_mode == VoltageCalcModes.AVG:
            u_in = sum(u_mag) / (len(u_mag) * kv_base)
        elif self._settings.voltage_calc_mode == VoltageCalcModes.MIN:
            u_in = min(u_mag) / kv_base
        elif self._settings.voltage_calc_mode == VoltageCalcModes.A:
            u_in = u_mag[0] / kv_base
        elif self._settings.voltage_calc_mode == VoltageCalcModes.B:
            u_in = u_mag[1] / kv_base
        elif self._settings.voltage_calc_mode == VoltageCalcModes.C:
            u_in = u_mag[3] / kv_base
        else:
            u_in = max(u_mag) / kv_base

        p_pv = abs(sum(self._controlled_element.GetVariable('Powers')[::2]))
        p_calc = p_pv / self._s_rated
        q_pv = -sum(self._controlled_element.GetVariable('Powers')[1::2])
        q_pv = q_pv / self._s_rated

        q_calc = 0
        if u_in <= self._settings.u_min:
            q_calc = self.q_lim_pu
        elif u_in <= self._settings.u_db_min and u_in > self._settings.u_min:
            m1 = self.q_lim_pu / (self._settings.u_min - self._settings.u_db_min)
            c1 = self.q_lim_pu * self._settings.u_db_min / (self._settings.u_db_min - self._settings.u_min)
            q_calc = u_in * m1 + c1
        elif u_in <= self._settings.u_db_max and u_in > self._settings.u_db_min:
            q_calc = 0
        elif u_in <= self._settings.u_max and u_in > self._settings.u_db_max:
            m2 = self.q_lim_pu / (self._settings.u_db_max - self._settings.u_max)
            c2 = self.q_lim_pu * self._settings.u_db_max / (self._settings.u_max - self._settings.u_db_max)
            q_calc = u_in * m2 + c2
        elif u_in >= self._settings.u_max:
            q_calc = -self.q_lim_pu

        q_calc = q_pv + (q_calc - q_pv) * 0.5 / self._damp_coef + (q_pv - self.old_q_pv) * 0.1 / self._damp_coef

        if p_calc > 0:
            if self._controlled_element.NumPhases == 2:
                self._controlled_element.SetParameter('kvar', q_calc * self._s_rated * 1.3905768334328491495461135972974)
            else:
                self._controlled_element.SetParameter('kvar', q_calc * self._s_rated)
        else:
            pass

        error = abs(q_pv- self.old_q_pv)
        self.old_q_pv = q_pv

        return error

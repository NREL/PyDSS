from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract
import gym_electric_motor as gem
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cmath

class motor3phs(ControllerAbstract):
    """The controller locks a regulator in the event of reverse power flow. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

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

    def __init__(self, LoadObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(motor3phs, self).__init__(LoadObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.Solver = dssSolver     
        self.Time = 0
        self.dt = dssSolver.GetStepResolutionSeconds()
        self._Settings = Settings
        self._ControlledElm = LoadObj
        self._eClass, self._eName = self._ControlledElm.GetInfo()
        self._Name = 'pyCont_' + self._eClass + '_' + self._eName
        self._ElmObjectList = ElmObjectList
        self.nPhases = self._ControlledElm.NumPhases
        assert self.nPhases == 3, "The model can only be coupled to three phase load models." 
        
        self.FREQ = dssInstance.Solution.Frequency()
        self.vBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        
        self.env = gem.make(
            # Choose the squirrel cage induction motor (SCIM) with continuous-control-set
            "AbcCont-TC-SCIM-v0",

            # Define the numerical solver for the simulation
            ode_solver="scipy.ode",

            # Define which state variables are to be monitored concerning limit violations
            # "()" means, that limit violation will not necessitate an env.reset()
            constraints=(),

            # Set the sampling time
            tau = dssSolver.GetStepResolutionSeconds()
        )
        tau = self.env.physical_system.tau
        self.limits = self.env.physical_system.limits
    
        (state, reference) = self.env.reset()

        self.STATE = np.transpose(np.array([state * self.limits]))
        self.TIME = np.array([0])
        P, Q = self.Power()
        self.P = [P]
        self.Q = [Q]
        return

    def Name(self):
        return self.Name

    def ControlledElement(self):
        return "{}.{}".format(self._eClass, self._eName)
    
    def debugInfo(self):
        return [self._Settings['Control{}'.format(i+1)] for i in range(3)]
    
    def Power(self):
        Id = self.STATE[5,-1]
        Iq = self.STATE[6,-1]
        Ud = self.STATE[10,-1]
        Uq = self.STATE[11,-1]
        P = 3/2 * (Ud * Id + Uq * Iq)
        Q = 3/2 * (Uq * Id - Ud * Iq)
        return P / 1000.0, Q / 1000.0
    
    
    def Update(self, Priority, Time, UpdateResults):
        if Priority == 0 :
            Vt = self.AvgVoltages()
            (state, reference), reward, done, _ = self.env.step(Vt)
            self.STATE = np.append(self.STATE, np.transpose([state * self.limits]), axis=1)
            self.TIME = np.append(self.TIME, Time)
            
            P, Q = self.Power()
            self.P.append(P)
            self.Q.append(Q)
            
            self._ControlledElm.SetParameter("kw", P)
            self._ControlledElm.SetParameter("kvar", Q)

            if self.Solver.isLastTimestep:
                self.STATE = pd.DataFrame(self.STATE).T
                self.STATE.columns = ["omega", "T" , "i_sa", "i_sb" , "i_sc", "i_sd" , "i_sq", "u_sa" , "u_sb", "u_sc" , "u_sd", "u_sq" , "epsilon", "u_dc"]
                self.STATE["P"] = self.P
                self.STATE["Q"] = self.Q
                self.STATE["T x omega"] = (self.STATE["T"] * self.STATE["omega"] /  0.16666666666667) / 9.5488 
                self.STATE[["omega"]].plot()
                self.STATE[["T"]].plot()
                self.STATE[["i_sa", "i_sb" , "i_sc"]].plot()
                self.STATE[["u_sa" , "u_sb", "u_sc"]].plot()
                self.STATE[["epsilon"]].plot()
                self.STATE[["u_dc"]].plot()
                self.STATE[["P", "Q"]].plot()
                self.STATE[["T x omega"]].plot()
                plt.show()
        return 0

    def AvgVoltages(self):
        Vp = self._ControlledElm.GetVariable('VoltagesMagAng', convert=False)[: 2 * self.nPhases]
        Vp = np.array(Vp)
        Vavg = sum(Vp[0::2]) / 3.0
        print(Vavg)
        Vp = [
            cmath.rect(Vavg, 0),
            cmath.rect(Vavg, -2* cmath.pi /3),
            cmath.rect(Vavg, +2* cmath.pi /3)
        ]
        Vt = []
        for u in Vp :
            Vt.append(self.phasor_to_time(u))
        return Vt
        
        
    def Voltages(self):
        Vp = self._ControlledElm.GetVariable('Voltages', convert=False)[: 2 * self.nPhases]
        Vp = np.array(Vp)
        Vp = Vp[0::2] + 1j * Vp[1::2]
        Vt = []
        for u in Vp :
            Vt.append(self.phasor_to_time(u))
        return Vt
        
    def avg_voltage(self, u):
        
        return
    
        
    def phasor_to_time(self, u):
        assert isinstance(u, complex), "The input variable should be a complex number"
        mag, ang = cmath.polar(u) 
        #mag = mag / self.vBase * 240.0
        t = self.Solver.GetTotalSeconds()
        ua = 400.0 / self.STATE[13,-1] * cmath.cos(2 * cmath.pi * self.FREQ * t + ang)

        return ua.real
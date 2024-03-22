from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract

try:
    from pvder.simulation_utilities import SimulationResults
    from pvder.dynamic_simulation import DynamicSimulation
    from pvder.simulation_events import SimulationEvents
    from pvder.grid_components import Grid
    from pvder.DER_wrapper import DERModel
except ImportError:
    raise ImportError("""
        This controller requires installation of the PVDER module. 
        Use 'pip install pvder' to install the module and try running the simulation again.
        """ 
    )
#from pvder import utility_functions

import numpy as np
import math

class PvDynamic(ControllerAbstract):

    DEBUG_SIMULATION = False
    DEBUG_VOLTAGES = False
    DEBUG_CURRENTS = False
    DEBUG_POWER = False
    DEBUG_CONTROLLERS = True
    DEBUG_PLL = False
    DEBUG_SOLVER = True

    def __init__(self, VSCObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(PvDynamic, self).__init__(VSCObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.solver = dssSolver
        self.p_old = 0
        self.time = 0
        self.dt = dssSolver.GetStepResolutionSeconds()
        self._settings = Settings
        self._controlled_element = VSCObj
        self._e_class, self._e_name = self._controlled_element.GetInfo()
        self._name = 'pyCont_' + self._e_class + '_' + self._e_name
        self.n_phases = self._controlled_element.NumPhases
        self.freq = dssInstance.Solution.Frequency()

        self.events1 = SimulationEvents(verbosity = 'DEBUG')
        #self.grid1 = Grid(events=self.events1, unbalance_ratio_b=1.0, unbalance_ratio_c=1.0)
        self.voltage_base = Grid.Vbase#self._controlled_element.sBus[0].GetVariable('kVBase') * 1000
        stand_alone = False
        steady_state = Settings["STEADY_STATE"]
        rated_power_ac_va = Settings["RATED_POWER_AC_VA"]
        rated_power_dc_watts = Settings["RATED_POWER_DC_WATTS"]
        der_verbosity = 'DEBUG'
        config_file = r"C:\Users\alatif\Documents\GitHub\pvder\config_der.json"
        if self.n_phases == 1:
            self._Va = self.Voltages()
            self._Vrms = abs(self._Va )/math.sqrt(2)
            #print(f"\nmodel inputs: \nVa - {self._Va}, \nVrms - {self._Vrms}\nFreq - {self.freq}\nvBase - {self.voltage_base}\n")
            self._pv_model = DERModel(
                modelType= 'SinglePhase',
                powerRating = rated_power_dc_watts,
                Sinverter_rated = rated_power_ac_va,
                events=self.events1,
                configFile=config_file,
                Vrmsrated = self._Vrms,
                gridVoltagePhaseA = self._Va,
                gridFrequency=2 * math.pi * self.freq,
                derId=Settings["DER_ID"],
                standAlone = stand_alone,
                steadyStateInitialization=steady_state,
                verbosity = der_verbosity
                )
            
        elif self.n_phases == 3:
            self._Va, self._Vb, self._Vc = self.Voltages()
            self._Vrms = abs(self._Va ) / math.sqrt(2)
            self._pv_model = DERModel(
                modelType= 'ThreePhaseUnbalanced',
                powerRating = 250000,
                Sinverter_rated = 250000,
                events=self.events1,
                configFile=config_file,
                Vrmsrated = self._Vrms,
                gridVoltagePhaseA = self._Va,
                gridVoltagePhaseB = self._Vb,
                gridVoltagePhaseC = self._Vc,
                gridFrequency=2 * math.pi * self.freq,
                derId=Settings["DER_ID"],
                standAlone = stand_alone,
                steadyStateInitialization=steady_state,
                verbosity = der_verbosity
                )
    
        self.sim1 = DynamicSimulation(
            PV_model=self._pv_model.DER_model,
            events = self.events1,
            verbosity = 'INFO',
            solverType='odeint',
            LOOP_MODE=True
            )
        
        self.results1 = SimulationResults(
            simulation = self.sim1,
            PER_UNIT=True,
            verbosity = 'INFO'
            )
        
        # self._pv_model.show_parameter_dictionaries()
        # self._pv_model.show_parameter_types()
        
        self.update_model_parameters()

        self._pv_model.DER_model.MPPT_ENABLE = Settings["MPPT_ENABLE"]
        self._pv_model.DER_model.RAMP_ENABLE = Settings["RAMP_ENABLE"]
        self._pv_model.DER_model.VOLT_VAR_ENABLE = Settings["VOLT_VAR_ENABLE"]
        self._pv_model.DER_model.LVRT_ENABLE = Settings["LVRT_ENABLE"]
        self._pv_model.DER_model.HVRT_ENABLE = Settings["HVRT_ENABLE"]
        self._pv_model.DER_model.LFRT_ENABLE = Settings["LFRT_ENABLE"]
        self._pv_model.DER_model.DO_EXTRA_CALCULATIONS = Settings["DO_EXTRA_CALCULATIONS"]
        self._pv_model.DER_model.use_frequency_estimate=Settings["use_frequency_estimate"]
        self.sim1.jacFlag = Settings["jacFlag"]
        self.sim1.DEBUG_SIMULATION = self.DEBUG_SIMULATION
        self.sim1.DEBUG_VOLTAGES = self.DEBUG_VOLTAGES
        self.sim1.DEBUG_CURRENTS = self.DEBUG_CURRENTS
        self.sim1.DEBUG_POWER = self.DEBUG_POWER
        self.sim1.DEBUG_CONTROLLERS  = self.DEBUG_CONTROLLERS
        self.sim1.DEBUG_PLL = self.DEBUG_PLL
        self.sim1.PER_UNIT = True
        self.sim1.DEBUG_SOLVER  = self.DEBUG_SOLVER
        self.sim1.tStop = dssSolver.get_simulation_end_time()
        self.sim1.tInc = self.dt
        self._pv_model._del_t_frequency_estimate = self.sim1.tInc 

        self.results = []
    
        return

    def update_model_parameters(self):
        make_changes = any([
            self._settings["UPDATE_MODULE_PARAMETRS"],
            self._settings["UPDATE_INVERTER_PARAMETRS"],
            self._settings["UPDATE_CIRCUIT_PARAMETRS"],
            self._settings["UPDATE_CONTROLLER_PARAMETRS"],
            self._settings["UPDATE_STEADYSTATE_PARAMETRS"]
        ])
  
        module_parameters = {
            'Np': self._settings["Np"],
            'Ns': self._settings["Ns"],
            'Vdcmpp0': self._settings["Vdcmpp0"],
            'Vdcmpp_max': self._settings["Vdcmpp_max"],
            'Vdcmpp_min': self._settings["Vdcmpp_min"],
        }
        inverter_ratings = {
            'Vdcrated': self._settings["Vdcrated"],
            'Ioverload': self._settings["Ioverload"],
            'Vrmsrated': self._settings["Vrmsrated"],
            'Iramp_max_gradient_imag': self._settings["Iramp_max_gradient_imag"],
            'Iramp_max_gradient_real': self._settings["Iramp_max_gradient_real"],
        }   
        circuit_parameters = {
            'Rf_actual': self._settings["Rf_actual"],
            'Lf_actual': self._settings["Lf_actual"],
            'C_actual': self._settings["C_actual"],
            'Z1_actual': self._settings["Z1_actual_real"] +self._settings["Z1_actual_imag"] *1j,
            'R1_actual': self._settings["R1_actual"],
            'X1_actual': self._settings["X1_actual"],
        }
        controller_gains = {
            'Kp_GCC': self._settings["Kp_GCC"],
            'Ki_GCC': self._settings["Ki_GCC"],
            'Kp_DC': self._settings["Kp_DC"],
            'Ki_DC': self._settings["Ki_DC"],
            'Kp_Q': self._settings["Kp_Q"],
            'Ki_Q': self._settings["Ki_Q"],
            'wp': self._settings["wp"]
        }
        steadystate_values = {
            'iaI0': self._settings["iaI0"],
            'iaR0': self._settings["iaR0"],
            'maI0': self._settings["maI0"],
            'maR0': self._settings["maR0"],
        }
        
        if make_changes:
            self._pv_model.DER_model.initialize_parameter_dict(
                parameter_ID=self.ControlledElement(),
                source_parameter_ID=self._settings["DER_ID"]
                )
            
            if self._settings["UPDATE_MODULE_PARAMETRS"]:
                self._pv_model.DER_model.update_parameter_dict(
                    parameter_ID=self.ControlledElement(),
                    parameter_type='module_parameters',
                    parameter_dict= module_parameters
                    ) 
            if self._settings["UPDATE_INVERTER_PARAMETRS"]:
                self._pv_model.DER_model.update_parameter_dict(
                    parameter_ID=self.ControlledElement(),
                    parameter_type='inverter_ratings',
                    parameter_dict= inverter_ratings
                    )
            if self._settings["UPDATE_CIRCUIT_PARAMETRS"]:
                self._pv_model.DER_model.update_parameter_dict(
                    parameter_ID=self.ControlledElement(),
                    parameter_type='circuit_parameters',
                    parameter_dict= circuit_parameters
                    )
            if self._settings["UPDATE_CONTROLLER_PARAMETRS"]:
                self._pv_model.DER_model.update_parameter_dict(
                    parameter_ID=self.ControlledElement(),
                    parameter_type='controller_gains',
                    parameter_dict= controller_gains
                    )
            if self._settings["UPDATE_STEADYSTATE_PARAMETRS"]:
                self._pv_model.DER_model.update_parameter_dict(
                    parameter_ID=self.ControlledElement(),
                    parameter_type='steadystate_values',
                    parameter_dict= steadystate_values
                    )
            self._pv_model.DER_model.modify_DER_parameters(parameter_ID=self.ControlledElement())
            params = self._pv_model.DER_model.get_parameter_dictionary(parameter_type='all',parameter_ID=self.ControlledElement())
        return

    def Name(self):
        return self.Name

    def ControlledElement(self):
        return "{}.{}".format(self._e_class, self._e_name)

    def run_dynamic_model(self):
        sim_time_sec = self.solver.GetTotalSeconds()
        t_sim = [sim_time_sec,sim_time_sec + self.dt]
        if self.n_phases == 1:
            self._Va =  self.Voltages()

            self.sim1.run_simulation(
                gridVoltagePhaseA=self._Va / self.voltage_base , 
                y0= self.sim1.y0 , 
                t=t_sim
                )
        elif self.n_phases == 3:
            self._Va, self._Vb, self._Vc = self.Voltages()
            self.sim1.run_simulation(
                gridVoltagePhaseA=self._Va / self.voltage_base , 
                gridVoltagePhaseB=self._Vb / self.voltage_base , 
                gridVoltagePhaseC=self._Vc / self.voltage_base , 
                y0=self.sim1.y0, 
                t=t_sim
                )
        

        S_PCC = self._pv_model.DER_model.S_PCC * self._pv_model.DER_model.Sbase / 1000
        #print(f"kW {S_PCC.real}\nkvar {S_PCC.imag}")
        self._controlled_element.SetParameter("kw", S_PCC.real )
        self._controlled_element.SetParameter("kvar", S_PCC.imag)
        self.results.append({
            "Vdc" : self._pv_model.DER_model.Vdc * self._pv_model.DER_model.Vbase,
            "vta" : self._pv_model.DER_model.vta * self._pv_model.DER_model.Vbase,
            "Vtrms" : self._pv_model.DER_model.Vtrms * self._pv_model.DER_model.Vbase,
            "Vrms" : self._pv_model.DER_model.Vrms * self._pv_model.DER_model.Vbase,
            "Irms" : self._pv_model.DER_model.Irms * self._pv_model.DER_model.Ibase,
            "Ppv" : self._pv_model.DER_model.Ppv * self._pv_model.DER_model.Sbase  /1000,
            "S" : self._pv_model.DER_model.S * self._pv_model.DER_model.Sbase,
            "S_PCC" : self._pv_model.DER_model.S_PCC * self._pv_model.DER_model.Sbase,
            "active_power [kVA]": np.real(self._pv_model.DER_model.S_PCC * self._pv_model.DER_model.Sbase) / 1000.0,
            "reactive_power [kVA]": np.imag(self._pv_model.DER_model.S_PCC * self._pv_model.DER_model.Sbase) / 1000.0,
            "grid_voltage [p.u.]": self._Va / self.voltage_base,
        })
                  
    def Update(self, Priority, Time, UpdateResults):
        if Priority == 0 :
            self.run_dynamic_model()
            # if self.solver.is_last_timestep:
            #     import matplotlib.pyplot as plt
            #     import pandas as pd
                
            #     fig, axs = plt.subplots(3, 2)

            #     self.results = pd.DataFrame(self.results, index=self.solver.all_timestamps)
            #     print(self.results)
            #     self.results[["Ppv", "reactive_power [kVA]", "active_power [kVA]"]].plot(ax=axs[0, 0])
            #     self.results[["Vdc", "Vrms", "vta", "Vtrms"]].plot(ax=axs[0, 1])
            #     self.results[["Irms"]].plot(ax=axs[1, 0])
            #     self.results[["S", "S_PCC"]].plot(ax=axs[1, 1])
            #     self.results[["grid_voltage [p.u.]"]].plot(ax=axs[2, 0])
            #     self.results.plot.scatter(x='grid_voltage [p.u.]',  y='reactive_power [kVA]', c='DarkBlue', ax=axs[2, 1])
                
            #     plt.show()
            #     print(self.results)
        return 0

    def debugInfo(self):
        return [self._Settings['Control{}'.format(i+1)] for i in range(3)]

    def Voltages(self):
        self._V0 = self._controlled_element.GetVariable('Voltages', convert=False)[: 2 * self.n_phases]
        self._V0 = np.array(self._V0)
        self._V0 = self._V0[0::2] + 1j * self._V0[1::2]
        if self.n_phases == 1:
            return self._V0[0]
        elif self.n_phases == 3:  
            return self._V0[0], self._V0[1], self._V0[2]
        else:
            raise Exception("Only single or three phase models can be used")
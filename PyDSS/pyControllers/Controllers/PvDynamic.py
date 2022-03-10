from  PyDSS.pyControllers.pyControllerAbstract import ControllerAbstract

from pvder.simulation_utilities import SimulationResults
from pvder.dynamic_simulation import DynamicSimulation
from pvder.simulation_events import SimulationEvents
from pvder.grid_components import Grid
from pvder.DER_wrapper import DERModel
#from pvder import utility_functions

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math

class PvDynamic(ControllerAbstract):

    def __init__(self, VSCObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(PvDynamic, self).__init__(VSCObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.Solver = dssSolver
        self.P_old = 0
        self.Time = 0
        self.dt = dssSolver.GetStepResolutionSeconds()
        self._Settings = Settings
        self._ControlledElm = VSCObj
        self._eClass, self._eName = self._ControlledElm.GetInfo()
        self._Name = 'pyCont_' + self._eClass + '_' + self._eName
        self._ElmObjectList = ElmObjectList
        self.nPhases = self._ControlledElm.NumPhases
        self.FREQ = dssInstance.Solution.Frequency()
        self.events1 = SimulationEvents(verbosity = 'DEBUG')
        self.grid1 = Grid(events=self.events1, unbalance_ratio_b=1.0, unbalance_ratio_c=1.0)
        self.vBase = self._ControlledElm.sBus[0].GetVariable('kVBase') * 1000
        STAND_ALONE = False
        STEADY_STATE = Settings["STEADY_STATE"]
        RATED_POWER_AC_VA = Settings["RATED_POWER_AC_VA"]
        RATED_POWER_DC_WATTS = Settings["RATED_POWER_DC_WATTS"]
        der_verbosity = 'DEBUG'
        config_file = r"C:\Users\alatif\Documents\GitHub\pvder\config_der.json"
        if self.nPhases == 1:
            self._Va = self.Voltages()
            self._Vrms = abs(self._Va )/math.sqrt(2)
            print(f"\nmodel inputs: \nVa - {self._Va}, \nVrms - {self._Vrms}\nFreq - {self.FREQ}\nvBase - {self.vBase}\n")
            self._pv_model = DERModel(
                modelType= 'SinglePhase',
                events=self.events1,
                configFile=config_file,
                Vrmsrated = self._Vrms,
                gridVoltagePhaseA = self._Va,
                gridFrequency=2 * math.pi * self.FREQ,
                derId=Settings["DER_ID"],
                standAlone = STAND_ALONE,
                steadyStateInitialization=STEADY_STATE,
                verbosity = der_verbosity
                )
            
        elif self.nPhases == 3:
            self._Va, self._Vb, self._Vc = self.Voltages()
            self._Vrms = abs(self._Va ) / math.sqrt(2)
            self._pv_model = DERModel(
                modelType= 'ThreePhaseUnbalanced',
                events=self.events1,
                configFile=config_file,
                Vrmsrated = self._Vrms,
                gridVoltagePhaseA = self._Va,
                gridVoltagePhaseB = self._Vb,
                gridVoltagePhaseC = self._Vc,
                gridFrequency=2 * math.pi * self.FREQ,
                derId=Settings["DER_ID"],
                standAlone = STAND_ALONE,
                steadyStateInitialization=STEADY_STATE,
                verbosity = der_verbosity
                )
            
        self.sim1 = DynamicSimulation(
            gridModel=self.grid1,
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

        self._pv_model.DER_model.MPPT_ENABLE=Settings["MPPT_ENABLE"]
        self._pv_model.DER_model.RAMP_ENABLE = Settings["RAMP_ENABLE"]
        self._pv_model.DER_model.VOLT_VAR_ENABLE = Settings["VOLT_VAR_ENABLE"]
        self._pv_model.DER_model.LVRT_ENABLE = Settings["LVRT_ENABLE"]
        self._pv_model.DER_model.HVRT_ENABLE = Settings["HVRT_ENABLE"]
        self._pv_model.DER_model.LFRT_ENABLE = Settings["LFRT_ENABLE"]
        self._pv_model.DER_model.DO_EXTRA_CALCULATIONS = Settings["DO_EXTRA_CALCULATIONS"]
        self._pv_model.DER_model.use_frequency_estimate=Settings["use_frequency_estimate"]
        self.sim1.jacFlag = Settings["jacFlag"]
        self.sim1.DEBUG_SIMULATION = Settings["DEBUG_SIMULATION"]
        self.sim1.DEBUG_VOLTAGES = Settings["DEBUG_VOLTAGES"]
        self.sim1.DEBUG_CURRENTS = Settings["DEBUG_CURRENTS"]
        self.sim1.DEBUG_POWER = Settings["DEBUG_POWER"]
        self.sim1.DEBUG_CONTROLLERS  = Settings["DEBUG_CONTROLLERS"]
        self.sim1.DEBUG_PLL = Settings["DEBUG_PLL"]
        self.sim1.PER_UNIT = True#Settings["PER_UNIT"]
        self.sim1.DEBUG_SOLVER  = Settings["DEBUG_SOLVER"]
        self.sim1.tStop = dssSolver.GetSimulationEndTimeSeconds()
        self.sim1.tInc = self.dt
        self._pv_model._del_t_frequency_estimate = self.sim1.tInc 

        self.results = []
    
        return

    def update_model_parameters(self):
        if self._Settings["UPDATE_PARAMETRS"]:
            module_parameters = {
                'Np': self._Settings["Np"],
                'Ns': self._Settings["Ns"],
                'Vdcmpp0': self._Settings["Vdcmpp0"],
                'Vdcmpp_max': self._Settings["Vdcmpp_max"],
                'Vdcmpp_min': self._Settings["Vdcmpp_min"],
            }
            inverter_ratings = {
                'Vdcrated': self._Settings["Vdcrated"],
                'Ioverload': self._Settings["Ioverload"],
                'Vrmsrated': self._Settings["Vrmsrated"],
                'Iramp_max_gradient_imag': self._Settings["Iramp_max_gradient_imag"],
                'Iramp_max_gradient_real': self._Settings["Iramp_max_gradient_real"],
            }   
            circuit_parameters = {
                'Rf_actual': self._Settings["Rf_actual"],
                'Lf_actual': self._Settings["Lf_actual"],
                'C_actual': self._Settings["C_actual"],
                'Z1_actual': self._Settings["Z1_actual_real"] +self._Settings["Z1_actual_imag"] *1j,
                'R1_actual': self._Settings["R1_actual"],
                'X1_actual': self._Settings["X1_actual"],
            }
            controller_gains = {
                'Kp_GCC': self._Settings["Kp_GCC"],
                'Ki_GCC': self._Settings["Ki_GCC"],
                'Kp_DC': self._Settings["Kp_DC"],
                'Ki_DC': self._Settings["Ki_DC"],
                'Kp_Q': self._Settings["Kp_Q"],
                'Ki_Q': self._Settings["Ki_Q"],
                'wp': self._Settings["wp"]
            }
            steadystate_values = {
                'iaI0': self._Settings["iaI0"],
                'iaR0': self._Settings["iaR0"],
                'maI0': self._Settings["maI0"],
                'maR0': self._Settings["maR0"],
            }
                
            self._pv_model.initialize_parameter_dict(
                parameter_ID=self.ControlledElement(),
                source_parameter_ID=self._Settings["DER_ID"]
                )
            
            # DER_parameters = self._pv_model.get_parameter_dictionary(
            #     parameter_type='all',
            #     parameter_ID= self._Settings["DER_ID"]
            #     )   
            
            self._pv_model.update_parameter_dict(
                parameter_ID=self.ControlledElement(),
                parameter_type='module_parameters',
                parameter_dict= module_parameters
                ) 
            self._pv_model.update_parameter_dict(
                parameter_ID=self.ControlledElement(),
                parameter_type='circuit_parameters',
                parameter_dict= circuit_parameters
                )
            self._pv_model.update_parameter_dict(
                parameter_ID=self.ControlledElement(),
                parameter_type='inverter_ratings',
                parameter_dict= inverter_ratings
                )
            self._pv_model.update_parameter_dict(
                parameter_ID=self.ControlledElement(),
                parameter_type='controller_gains',
                parameter_dict= controller_gains
                )
            
            self._pv_model.update_parameter_dict(
                parameter_ID=self.ControlledElement(),
                parameter_type='steadystate_values',
                parameter_dict= steadystate_values
                )
            self._pv_model.modify_DER_parameters(parameter_ID=self.ControlledElement())
            #params = self._pv_model.get_parameter_dictionary(parameter_type='all',parameter_ID=self.ControlledElement())
        return

    def Name(self):
        return self.Name

    def ControlledElement(self):
        return "{}.{}".format(self._eClass, self._eName)

    def run_dynamic_model(self):
        sim_time_sec = self.Solver.GetTotalSeconds()
        t_sim = [sim_time_sec,sim_time_sec + self.dt]
        if self.nPhases == 1:
            self._Va =  self.Voltages()
            print(f"Grid voltage: {self._Va}")
            self.sim1.run_simulation(
                gridVoltagePhaseA=self._Va / self.vBase, 
                y0= self.sim1.y0 , 
                t=t_sim
                )
        elif self.nPhases == 3:
            self._Va, self._Vb, self._Vc = self.Voltages()
            self.sim1.run_simulation(
                gridVoltagePhaseA=self._Va / self.vBase, 
                gridVoltagePhaseB=self._Vb / self.vBase, 
                gridVoltagePhaseC=self._Vc / self.vBase, 
                y0=self.sim1.y0, 
                t=t_sim
                )
        
        self.results.append({
            "Vdc" : self._pv_model.DER_model.Vdc * self._pv_model.DER_model.Vbase,
            "vta" : self._pv_model.DER_model.vta * self._pv_model.DER_model.Vbase,
            "Vtrms" : self._pv_model.DER_model.Vtrms * self._pv_model.DER_model.Vbase,
            "Vrms" : self._pv_model.DER_model.Vrms * self._pv_model.DER_model.Vbase,
            "Irms" : self._pv_model.DER_model.Irms * self._pv_model.DER_model.Ibase,
            "Ppv" : self._pv_model.DER_model.Ppv * self._pv_model.DER_model.Sbase,
            "S" : self._pv_model.DER_model.S * self._pv_model.DER_model.Sbase,
            "S_PCC" : self._pv_model.DER_model.S_PCC * self._pv_model.DER_model.Sbase,
            # "mb" : self._pv_model.mb,
            # "mc" : self._pv_model.mc,
            # "m_sum" : self._pv_model.ma + self._pv_model.mb + self._pv_model.mc,  
        })
           
        
        
    def Update(self, Priority, Time, UpdateResults):
        if Priority == 0 :
            self.run_dynamic_model()
            if self.Solver.isLastTimestep:
                self.results = pd.DataFrame(self.results, index=self.Solver.allTimestamps)
                print(self.results)
                #self.results["Ppv"].plot()
                self.results["S"].plot()
                plt.show()
                print(self.results)
        return 0

    def debugInfo(self):
        return [self._Settings['Control{}'.format(i+1)] for i in range(3)]

    def Voltages(self):
        self._V0 = self._ControlledElm.GetVariable('Voltages', convert=False)[: 2 * self.nPhases]
        self._V0 = np.array(self._V0)
        self._V0 = self._V0[0::2] + 1j * self._V0[1::2]
        if self.nPhases == 1:
            return self._V0[0]
        elif self.nPhases == 3:  
            return self._V0[0], self._V0[1], self._V0[2]
        else:
            raise Exception("Only single or three phase models can be used")
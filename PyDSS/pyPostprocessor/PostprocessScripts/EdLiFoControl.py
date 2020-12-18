#**Authors:**
# Akshay Kumar Jain; Akshay.Jain@nrel.gov

from PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
from PyDSS.exceptions import InvalidParameter, OpenDssConvergenceError
# Additional packages
import os
import matplotlib.pyplot as plt
import csv
import pandas as pd
import math
import opendssdirect as dss
import networkx as nx
import time
import json
import numbers
# from place_new_regs import place_new_regs
import numpy as np
import seaborn as sns
import scipy.spatial.distance as ssd
from sklearn.cluster import AgglomerativeClustering
import matplotlib.image as mpimg
from PyDSS.pyPostprocessor.PostprocessScripts.postprocess_thermal_upgrades import postprocess_thermal_upgrades
from PyDSS.utils.utils import iter_elements, check_redirect
plt.rcParams.update({'font.size': 14})

# For an overloaded line if a sensible close enough line code is available then simply change the line code
#  else add a new line in parallel
# Does not correct switch thermal violations if any - will only work on line objects which are not marked as switches
# In this part of the code since lines and DTs
# The available upgrades options can be read from an external library as well, currently being created by reading
#  through the DTs and lines available in the feeder itself.
# TODO: Add xhl, xht, xlt and buses functionality for DTs
# TODO: Units of the line and transformers
# TODO: Correct line and xfmr violations safety margin issue

#
#--------------- Setting POA Parameters -------------
    # curtail_option = 'pctpmpp' # can be 'kva' or 'pctpmpp', default='pctpmpp'
    # deployment_path = PV_Scenario_DSS_Filename
    # directory, deployment_name = os.path.split(deployment_path)
    # fixed_pv_path = None # or the path to fixed existing PVs 
    # user_lifo_pv_list = [] # list of predetermined edLiFo candidate PVs
    
    # deployment_name = deployment_name.split('.')[0]
    # #overload_file = os.path.join(run_folder,'export','thermal_overloads.csv')
    # #CurtailmentLog = dict()
    # curtailment_size = 50
    
    # electrical_distance_file_path = os.path.join(feeder_path,'edistance.csv')
    
    # if not os.path.exists(electrical_distance_file_path):
        # dismat_df = compute_electrical_distance(Master_OpenDSS_Filename)
        # dismat_df.to_csv(electrical_distance_file_path)
    # else:
        # dismat_df = pd.read_csv(electrical_distance_file_path, index_col=0)
    # avg_distance, std_distance, dispersion_factor, zone_thr = choose_zone_radius(dismat_df)
    # if len(dismat_df.iloc[:,0])==0:
        # zone_thr = 0.0012 # Hack!!!
        # print('\x1b[6;30;42m' +'ELECTRICAL DISTANCE MATRIX NOT COMPUTED !!!'+ '\x1b[0m')
    # zone_option = 'Yes'
    # #zone_thr = 0.175
    # zone_thr = 0.5*zone_thr  # zone radius sensitivity analysis!!!
    # #curtail_option = 'pctpmpp' # can be 'kva' or 'pctpmpp', default='pctpmpp'
    # pvdict,pvdf = parse_pv_scenario(deployment_path)
    # pvdf3 = pvdf[pvdf['phases']=='3'].copy()
    # monitored_lines = get_monitored_line_dataframe("all") # extracting the set of lines that are monitored by POA. Default: All 3-phase lines
    
    # export_path = os.path.join(run_folder,'results',str(deployment), str(penetration))
    # if not os.path.exists(export_path):
        # os.makedirs(export_path,exist_ok=True)
#--------------------------------------------------------------------------


# to get xfmr information
def get_transformer_info():
    xfmr_name = dss.Transformers.Name()
    data_dict = {"name": xfmr_name, "num_phases": dss.Properties.Value("Phases"),
                 "num_wdgs": dss.Transformers.NumWindings(), "kva": [], "conn": [], "kv": []}
    for wdgs in range(data_dict["num_wdgs"]):
        dss.Transformers.Wdg(wdgs + 1)
        data_dict["kva"].append(float(dss.Properties.Value("kva")))
        data_dict["kv"].append(float(dss.Properties.Value("kv")))
        data_dict["conn"].append(dss.Properties.Value("conn"))
    return data_dict
    
def get_g(x):
    return float(str(x[0]).split('|')[0])**(-1)

def compute_electric_distance():
    
    lines = dss.utils.lines_to_dataframe()
    
    column_list = [c.strip().lower() for c in lines.columns]
    
    lines.columns = column_list
    
    lines['phases'] = pd.to_numeric(lines['phases'])
    lines3=lines.loc[lines['phases']==3,['bus1','bus2','rmatrix']].copy()
    
    lines3['g']=lines3['rmatrix'].apply(get_g)
    busall = np.unique((list(lines3['bus1']) + list(lines3['bus2'])))
    disGmat_df = pd.DataFrame(0, index=busall, columns=busall)
    
    for l in lines3.index:
        disGmat_df.loc[lines3.loc[l,'bus1'],lines3.loc[l,'bus2']] = -lines3.loc[l,'g']
        disGmat_df.loc[lines3.loc[l,'bus2'],lines3.loc[l,'bus1']] = -lines3.loc[l,'g']
        
    for b in busall:
        disGmat_df.loc[b,b]=-sum(disGmat_df.loc[b,:])
        
    disRmat_df = pd.DataFrame(np.linalg.pinv(np.array(disGmat_df)),
                              index=disGmat_df.index, 
                              columns=disGmat_df.columns)
    
    dismat_df = pd.DataFrame(0, index=busall, columns=busall)
    for i in disGmat_df.index:
        for j in disGmat_df.columns:
            dismat_df.loc[i,j] = disRmat_df.loc[i,i]+disRmat_df.loc[j,j]-disRmat_df.loc[i,j]-disRmat_df.loc[j,i]
            
    
    return dismat_df
    
    def choose_zone_radius(dismat_df):
        avg_distance = np.mean(np.array(dismat_df))
        std_distance = np.std(np.array(dismat_df))
        dispersion_factor = std_distance/avg_distance
        k=-0.8 # zone_radius calibration factor bounded by the inverse of the dispersion factor
        if abs(k)>1/dispersion_factor:
            k=-0.8/dispersion_factor # to avoid negative zone radius
        zone_thr=round(avg_distance+k*std_distance,4)
        return avg_distance, std_distance, dispersion_factor, zone_thr
        
    def parse_pv_scenario(file_path, min_lifo_pv_size):
        """
        Extract from a PV deployment scenario, parameter information into a dataframe.
        Sample syntax:
            PV_dict, PV_dataframe = parse_pv_scenario(deployment_path + deployment_name)
        """
        
        PVsys_dict = dict() 
        attribute_list = ['phases','bus1','kV','irradiance','Pmpp','pf','conn','kVA','%cutin','%cutout','Vmaxpu']
        
        if os.path.exists(file_path):
        
            with open(file_path,"r") as depfile:
                for line in depfile.readlines():
                    pvname = line.split('PVSystem.')[1].split()[0].lower()
                    PVsys_dict[pvname]=dict()
                    PVsys_dict[pvname]['pvname']=pvname
                    for att in attribute_list:
                        PVsys_dict[pvname][att] = string_attribute_parser(att,line)
        else:
            flag = dss.PVSystems.First()
            
            while flag > 0:
                pvname = dss.PVSystems.Name.lower()
                PVsys_dict[pvname]=dict()
                PVsys_dict[pvname]['pvname']=pvname
                
                for att in attribute_list:
                
                    if att in ['kV','irradiance','Pmpp','pf','kVA','%cutin','%cutout','Vmaxpu']:
                        PVsys_dict[pvname][att] = float(dss.Properties.Value(att))
                    else:
                        PVsys_dict[pvname][att] = dss.Properties.Value(att)
                        
                flag = dss.PVSystems.Next()
                
        return  PVsys_dict, pd.DataFrame.from_dict(PVsys_dict, 'index')   
        
    
    def get_monitored_line_dataframe(phase_info=3):
        """
        Sample syntax:
        monitored_lines = get_monitored_line_dataframe()
        """
        lines = dss.utils.lines_to_dataframe()
        column_list = [c.strip().lower() for c in lines.columns]
        lines.columns = column_list
        lines['phases'] = pd.to_numeric(lines['phases'])
        if phase_info !=3:
            monitored_lines = lines
        else:
            monitored_lines = lines.loc[lines['phases']==3,['bus1','bus2','rmatrix']].copy()
            
        return monitored_lines
        
    def check_line_overloads(monitored_lines):
        #monitored_lines = get_monitored_line_dataframe()
        ovrl = None
        
        overloaded_line_dict = dict()
        affected_buses = []
        dss.Circuit.SetActiveClass("Line")
        flag = dss.ActiveClass.First()
        while flag>0:
            line_name = dss.CktElement.Name()
            line_limit = dss.CktElement.NormalAmps()
            raw_current = dss.CktElement.Currents() 
            line_current = [math.sqrt(i**2+j**2) for i,j in zip(raw_current[::2], raw_current[1::2])]
            ldg = max(line_current)/float(line_limit)
            #if ldg > 1.0 and dss.CktElement.NumPhases==3:
            if ldg > 1.0:
                #print('Checking Line: ', line_name)
                #if line_name in monitored_lines.index:
                overloaded_line_dict[line_name]= ldg*100
                affected_buses.append(dss.CktElement.BusNames()[0])
                affected_buses.append(dss.CktElement.BusNames()[1])
                #affected_buses.append(monitored_lines.loc[line_name,'bus1'])
                #affected_buses.append(monitored_lines.loc[line_name,'bus2'])
            flag = dss.ActiveClass.Next()
        
        affected_buses = np.unique(list(affected_buses))
        
        if len(affected_buses)>0:
            ovrl = pd.DataFrame.from_dict(overloaded_line_dict, 'index')
            ovrl.columns = ['%normal']
        
        return ovrl, affected_buses
    
    def form_pvzones(affected_buses, dismat_df, zone_thr):
        #print('Affected buses:', affected_buses)
        ohmy = dismat_df.loc[affected_buses,:].copy()
        zone=list()
        for col in ohmy.columns:
            if min(ohmy.loc[:,col])<=zone_thr:
                zone.append(col)
        
        return zone
    


class EdLiFoControl(AbstractPostprocess):
    """The class is used to induce faults on bus for dynamic simulation studies. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class. 

    :param FaultObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type FaultObj: class:`PyDSS.dssElement.dssElement`
    :param Settings: A dictionary that defines the settings for the faul controller.
    :type Settings: dict
    :param dssInstance: An :class:`opendssdirect` instance
    :type dssInstance: :class:`opendssdirect` instance
    :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit ojects
    :type ElmObjectList: dict
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`
    :raises: AssertionError  if 'FaultObj' is not a wrapped OpenDSS Fault element

    """
    REQUIRED_INPUT_FIELDS = ["curtailment_size",
                             "electrical_distance_file_path",
                             "zone_option",
                             "zone_threshold",
                             "fixed_pv_path",
                             "lifo_pv_path",
                             "lifo_min_pv_size",
                             "user_lifo_pv_list" ]
    # REQUIRED_INPUT_FIELDS = (
        # "line_loading_limit",
        # "dt_loading_limit",
        # "line_safety_margin",
        # "xfmr_safety_margin",
        # "nominal_voltage",
        # "max_iterations",
        # "create_upgrade_plots",
        # "tps_to_test",
        # "create_upgrades_library",
		# "upgrade_library_path",
    # )

    def __init__(self, project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
        """
		Constructor method
        """
        super(EdLiFoControl, self).__init__(project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger)
        
        if isinstance(self.config["curtailment_size"], numbers.Number):
            self.curtailment_size = self.config["curtailment_size"]
        else:
            self.curtailment_size = 20
        
        self.electrical_distance_file_path = self.config["electrical_distance_file_path"]
        
        if not os.path.exists(self.electrical_distance_file_path):
            self.electrical_distance_file_path = os.path.join(self.config["Inputs"], "edistance.csv")
            self.dismat_df = compute_electric_distance()
            self.dismat_df.to_csv(self.electrical_distance_file_path)
            
        else:
            
            self.dismat_df = pd.read_csv(self.electrical_distance_file_path, index_col=0)
            
        self.avg_distance, self.std_distance, self.dispersion_factor, self.zone_threshold = choose_zone_radius(self.dismat_df)
        self.zone_option = self.config["zone_option"]
        
        if isinstance(self.config["zone_threshold"], numbers.Number):
            self.zone_threshold = self.config["zone_threshold"]
            
        if os.path.exists(self.config["fixed_pv_path"]):
            self.fixed_pv_path = self.config["fixed_pv_path"]
        else:
            self.fixed_pv_path = None
            
        if os.path.exists(self.config["lifo_pv_path"]):
            self.lifo_pv_path = self.config["lifo_pv_path"]
        else:
            self.lifo_pv_path = None
            
        self.lifo_min_pv_size = self.config["lifo_min_pv_size"]
        self.user_lifo_pv_list = self.config["user_lifo_pv_list"]
        self.pvdict, self.pvdf = parse_pv_scenario(self.lifo_pv_path, self.lifo_min_pv_size)
        self.pvdf3 = self.pvdf[self.pvdf['phases']=='3'].copy()
        self.export_path = os.path.join(self.config["Outputs"])
        self.monitored_lines = get_monitored_line_dataframe("all")
        
        
        
        
        
    
    def poa_curtail(self):
        #curtail_option can be 'kva' or 'pctpmpp'
        dss.run_command("set stepsize=0")
        dss.run_command("BatchEdit PVSystem.* VarFollowInverter=True") 
        self.pvs_df = dss.utils.pvsystems_to_dataframe()
        
        #print("PV columns:",pvs_df.columns)
        #orded_pv_df = pvs_df.sort_values(['Idx'])
        self.orded_pv_df = self.pvs_df.sort_values(['Idx'], ascending=False)
        
        if self.user_lifo_pv_list is None:
            self.poa_lifo_ordered_pv_list=list(self.orded_pv_df.index)
            self.poa_lifo_ordered_pv_list = [p for p in self.poa_lifo_ordered_pv_list if p in list(self.pvdf3.index)]
        else:
            self.poa_lifo_ordered_pv_list = self.user_lifo_pv_list
            
        
        
        #dss.Circuit.SetActiveClass("PVsystems")
        #print(f"PV names found: {dss.ActiveClass.AllNames()}")
        
        
        self.PV_curtailed = dict()
        self.PV_kW_curtailed = dict()
        self.pvbus_voltage = dict()
        self.solution_status = -1
        self.comment = 'RAS'
        self.total_kVA_deployed = sum(self.pvs_df['kVARated'])
        self.total_init_kW_deployed = 0
        #print("Total PV KVA deployed: ",total_kVA_deployed)
        self.total_kVA_curtailed = 0
        self.total_kW_curtailed = 0
        self.total_kW_output = 0
        self.Pct_kW_curtailment = 0
        
        for pv_sys in self.poa_lifo_ordered_pv_list:
            #pv_sys_n = remove_pen(pv_sys)
            self.PV_curtailed[pv_sys] = 0
            self.pvbus_voltage[pv_sys] = []
            #PV_kW_curtailed[pv_sys_n] = 0
            self.PV_kW_curtailed[pv_sys+'NetCurt'] = 0
            self.PV_kW_curtailed[pv_sys+'kWCurt'] = 0
            self.PV_kW_curtailed[pv_sys+'PctCurt'] = 0
            self.PV_kW_curtailed[pv_sys+'PctPmpp'] = 100
        
        #PV_available = dict()
        #overloads_df,affected_buses = check_overloads(export_path)
        self.overloads_df, self.affected_buses = check_line_overloads(self.monitored_lines)
        print('Number of buses affected:', len(self.affected_buses))
        
        self.zone=[]
        
        if len(self.affected_buses)>0:
            
            self.zone = form_pvzones(self.affected_buses, self.dismat_df, self.zone_threshold)
            #print('zone length:',len(zone))
            
        else:
            print('No monitored line affected')
        
        self.lifo_pv_list=[]
        for pv in self.poa_lifo_ordered_pv_list:
            if (self.user_lifo_pv_list is None) :
                if self.pvdf3.loc[pv,'bus1'] in self.zone:
                    self.lifo_pv_list.append(pv)
            else:
                dss.Circuit.SetActiveElement('PVSystem.'+str(pv))
                bus1 = dss.Properties.Value("bus1")
                if bus1 in self.zone:
                    self.lifo_pv_list.append(pv)
            
            
        self.lifo_pv_list = list(self.lifo_pv_list)
        if len(self.lifo_pv_list)==0 and len(self.zone)>0:
            self.comment = f'No PV system found in the vicinity (radius={self.zone_threshold}) of the thermal overload'
            #print(comment)
        
        if self.zone_option=='Yes' and len(self.lifo_pv_list)>0:
            self.my_lifo_list = self.lifo_pv_list + [x for x in self.poa_lifo_ordered_pv_list if not x in self.lifo_pv_list]
            #print('In-zone PV plants:', my_lifo_list)
            #print('zone_radius', zone_thr)
        else:
            self.my_lifo_list = self.poa_lifo_ordered_pv_list
        
        
        #while not list(overloads_df.index)==[]:
        self.solution_status = 0
        #print(pvs_df)
        if max(self.pvs_df.loc[self.poa_lifo_ordered_pv_list,'kVARated'])==0:
            self.comment='No PV system found!'
            print(self.comment)
            try:
                self.ov = self.overloads_df
                #print('Here are the persisting overloads:')
                #print(list(ov.index))
            except:
                pass
                    
            
        #break
        elif len(self.my_lifo_list)>0:
            
            #for pv_sys in poa_lifo_ordered_pv_list:
            self.init_pctpmpp={}
            self.init_kVA={}
            self.init_net_power_PV = 0
            self.init_power_PV=[]
            
            
            for pv_sys in self.my_lifo_list:
                
                dss.Circuit.SetActiveClass("PVsystems")
                
                if not dss.Circuit.SetActiveElement(f"PVSystem.{pv_sys}")>0:
                    print(f"Cannot find the PV system {pv_sys}")
                    print("Active element index:", dss.Circuit.SetActiveElement(f"PVSystem.{pv_sys}"))
                    break
                else:
                    dss.Circuit.SetActiveElement(f"PVSystem.{pv_sys}")
                    self.init_power_PV = dss.CktElement.Powers()
                    self.init_net_power_PV = sum(init_power_PV[::2])
                    if dss.Properties.Value('pctPmpp')=='':
                        self.init_pctpmpp[pv_sys] = 100
                        self.oldpctpmpp = 100
                        dss.run_command(f"Edit PVSystem.{pv_sys} pctPmpp=100")
                    else:
                        self.init_pctpmpp[pv_sys] = int(dss.Properties.Value('pctPmpp'))
                        self.init_kVA[pv_sys] = int(dss.Properties.Value('kVA'))
                        self.oldpctpmpp = self.init_pctpmpp[pv_sys]
                
                
                while len(self.affected_buses)>0 and self.pvs_df.loc[pv_sys,'kVARated']>0 and self.oldpctpmpp>0:
                    dss.Circuit.SetActiveElement(f"PVSystem.{pv_sys}")
                    
                    if self.curtail_option=='pctpmpp':
                        
                        print(f"Old pctpmpp: {self.oldpctpmpp}")
                        self.newpctpmpp = max(self.oldpctpmpp-5,0)
                        
                        
                        dss.run_command(f"Edit PVSystem.{pv_sys} pctPmpp={self.newpctpmpp}")
                        if self.newpctpmpp==0:
                            self.kvarlimit = 0
                            dss.run_command(f"Edit PVSystem.{pv_sys} kvarLimit={self.kvarlimit}")
                        self.npc = int(dss.Properties.Value('pctPmpp'))
                        print(f"New pctpmpp: {self.npc}")
                        self.PV_kW_curtailed[pv_sys+'PctPmpp'] = self.newpctpmpp
                    else:
                        self.PV_curtailed[pv_sys] += min(self.curtailment_size, self.pvs_df.loc[pv_sys,'kVARated'])
                        self.new_kVA = max(self.pvs_df.loc[pv_sys,'kVARated'] - self.curtailment_size,0)
                        dss.run_command(f"Edit PVSystem.{pv_sys} kVA={self.new_kVA}")
                    
                    dss.run_command("_SolvePFlow")
                    
                    self.overloads_df, self.affected_buses = check_line_overloads(self.monitored_lines)
                    self.pvs_df = dss.utils.pvsystems_to_dataframe()
                    
                    if self.curtail_option == 'pctpmpp':
                        self.oldpctpmpp = newpctpmpp
                        if len(self.affected_buses)>0 and self.oldpctpmpp==0:
                            self.comment=f"{pv_sys} is fully curtailed but overloads still exist!"
                        else:
                            pass
                            
                    elif self.curtail_option=='kva':
                        if len(self.affected_buses)>0 and max(self.pvs_df.loc[self.poa_lifo_ordered_pv_list,'kVARated'])==0:
                            self.comment='All PV systems have been curtailed, but overloads still exist!'
                        
                    
                    if len(self.affected_buses)==0:
                        self.solution_status = 1
                        self.comment = "Overload Solved!"
                        print(self.comment)
                        
                        break
                        
                dss.Circuit.SetActiveElement(f"PVSystem.{pv_sys}")
                self.avail_power = [x['Pmpp']*dss.Properties.Value('mult') for k, x in self.pvdict.items() if pv_sys == k][0]
                self.power_PV = dss.CktElement.Powers()
                self.net_power_PV = sum(self.power_PV[::2])
                self.net_kvar_PV = sum(self.power_PV[1::2])
                self.PV_kW_curtailed[pv_sys+'Ref'] = self.init_net_power_PV
                self.PV_kW_curtailed[pv_sys+'Actual'] = self.net_power_PV
                self.PV_kW_curtailed[pv_sys+'NetCurt'] = self.init_net_power_PV - self.net_power_PV
                self.PV_kW_curtailed[pv_sys+'PctCurt'] = 100*abs(self.init_net_power_PV - self.net_power_PV)/max(1,abs(self.avail_power))
                self.PV_kW_curtailed[pv_sys+'kVarActual'] = self.net_kvar_PV            

                self.total_kVA_curtailed += self.PV_curtailed[pv_sys]
                self.total_kW_curtailed += self.PV_kW_curtailed[pv_sys+'NetCurt']
                self.total_init_kW_deployed += self.PV_kW_curtailed[pv_sys+'Ref']
                self.total_kW_output += self.net_power_PV
                #print(total_kVA_curtailed)
               
                which_bus = dss.Properties.Value("bus1")
                dss.Circuit.SetActiveBus(which_bus)
                volt = dss.Bus.puVmagAngle()[::2]
                self.pvbus_voltage[pv_sys]=volt
                
            # Setting pmpps back to their original values    
            if self.init_kVA!={}:
                for pv_sys in self.my_lifo_list:
                    inipctpmpp = self.init_pctpmpp[pv_sys]
                    inikva = self.init_kVA[pv_sys]
                    dss.run_command(f"Edit PVSystem.{pv_sys} pctPmpp={inipctpmpp} kVA={inikva}")
                    
        if self.solution_status == -1:
            self.comment = "No need to curtail!"
            
        if max(self.PV_curtailed.keys(), key=(lambda k: self.PV_curtailed[k]))==0:
            self.comment = 'Deployment passed without curtailment!'
            #print(comment)
            self.solution_status == 0
        self.PV_curtailed['Comment'] = self.comment
        self.Pct_curtailment = self.total_kVA_curtailed*100/max(1, self.total_kVA_deployed)
        self.PV_curtailed['Pct_curtailment'] = self.Pct_curtailment 
        
        self.Pct_kW_curtailment = abs(self.total_kW_curtailed)*100/max(1,abs(self.total_init_kW_deployed))
        self.PV_kW_curtailed['Pct_kW_curtailment'] = self.Pct_kW_curtailment
        self.PV_kW_curtailed['Total_PV_kW_deployed'] = self.total_init_kW_deployed
        self.PV_kW_curtailed['Total_PV_kW_curtailed'] = self.total_kW_curtailed
        self.PV_kW_curtailed['Total_PV_kW_output'] = self.total_kW_output
        self.PV_kW_curtailed['Comment'] = self.comment
        #print("Done with 1 poa loop:", Pct_curtailment)
        
        return
        
        # return self.solution_status, self.PV_curtailed, self.PV_kW_curtailed, self.pvbus_voltage
        
        
            
            
            
            
        
        
        
        
        # edLiFo
        ##deployment_name,pvdf3,dismat_df, curtailment_size, export_path,zone_thr,zone_option,monitored_lines,curtail_option,user_lifo_pv_list
        print("edLiFo invoked!!!")
        #breakpoint()

    def run(self):
        pass

    def _get_required_input_fields(self):
        return self.REQUIRED_INPUT_FIELDS
        

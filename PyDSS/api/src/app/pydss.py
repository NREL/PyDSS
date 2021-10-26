import os
import logging
from multiprocessing import current_process
import inspect
from queue import Empty

import opendssdirect as dss

from PyDSS.dssInstance import OpenDSS
from PyDSS.api.src.app.model_creator.Scenario_generator import PyDSS_Model
from PyDSS.api.src.web.parser import restructure_dictionary
from PyDSS.api.src.app.JSON_writer import JSONwriter
from naerm_core.web.client_requests import send_sync_request
from naerm_core.notification.notifier import Notifier
import json
from http import HTTPStatus
from zipfile import ZipFile
import re
import shutil
import toml
import ast

logger = logging.getLogger(__name__)

class PyDSS:

    commands = {
        "run": None
    }

    def __init__(self, helics_, services, event=None, queue=None, parameters=None):

        self.initalized = False
        self.uuid = current_process().name

        ''' TODO: work on logging.yaml file'''
        
        logging.info("{} - initialized ".format({self.uuid}))

        self.shutdownevent = event
        self.queue = queue
        self.data_service_url = services['bes_data']
        notifications_uri = services['notifications_data']
        self.notifier = Notifier(notifications_uri)
        
        try:
            parameters['Broker'] = helics_['broker']['host']
            parameters['Broker port'] = helics_['broker']['port']
            parameters['Co-simulation Mode'] = True

            self.cosim_uuid = parameters['cosim_uuid']
            self.federate_service = 'der_federate_service'
            self.fed_name = parameters['name']
            self.parameters = parameters
            self.notify('Starting to initialize PyDSS ...........')
            
            """ If the project path is uuid, grab content from AWS S3"""
            if not os.path.exists(parameters["powerflow_options"]["pydss_project"]):
                self.notify("Initiating project creation process")
                parameters = self.update_project_params(parameters)
                if parameters is None:
                    self.queue({
                        "Status": 500,
                        "Message": "Error creating project",
                        "UUID": self.uuid
                    })
                    return

            else:
                self.project_folder = parameters['powerflow_options']['pydss_project']
                if 'sub_id' in parameters['powerflow_options']:
                    sub_id = parameters['powerflow_options'].pop('sub_id')
                    path_to_sub_file = os.path.join(self.project_folder, parameters['powerflow_options']['active_project'], 
                        'Scenarios', parameters['powerflow_options']['active_scenario'], 'ExportLists')
                    self.update_subscription_publications_in_toml_file(sub_id, path_to_sub_file)

            params = restructure_dictionary(parameters)
            
            self.time_resolution = params['Project']['Step resolution (sec)']/60
            params['Project']["Loadshape start time"] = "1/1/2020 00:00:00"

            # Making sure delta time is small enough
            params['Helics']['Time delta'] = 0.1*params['Project']['Step resolution (sec)']/60.0
            
            # Update federate name
            params['Helics']['Federate name'] = self.fed_name
            
            # Create PyDSS instance
            params['Profiles']["Use profile manager"] = False
            self.notify(f"PyDSS scenario > {params['Project']}")
            self.pydss_obj = OpenDSS(params, self.notify)
            export_path = os.path.join(self.pydss_obj._dssPath['Export'], params['Project']['Active Scenario'])
            Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
            self.a_writer = JSONwriter(export_path, self.data_service_url, Steps, self.notify)
            self.initalized = True
            self.notify("PyDSS projects initialized successfully")
        except Exception as e:
            result = {"Status": 500, "Message": f"Failed to create a PyDSS instance"}
            self.notify(f"PyDSS error occurred: {str(e)}", log_level=logging.ERROR)
            self.queue.put(result)
            return

        #self.RunSimulation()
        logger.info("{} - pydss dispatched".format(self.uuid))

        result = {
            "Status": 200,
            "Message": "PyDSS {} successfully initialized.".format(self.uuid),
            "UUID": self.uuid
        }

        if self.queue != None: self.queue.put(result)

        self.run(params={})
        #self.run_process()

    def notify(self, msg: str, timestep: float=None, log_level:
                                                    int=logging.INFO):
        """ Send notification to the notification client. """
        self.notifier.notify(self.cosim_uuid, self.federate_service, msg, 
                             timestep, log_level)

    def update_subscription_publications_in_toml_file(self, sub_id, path_to_sub_file):

        if os.path.exists(path_to_sub_file):
            if 'Subscriptions.toml' in os.listdir(path_to_sub_file):
                os.remove(os.path.join(path_to_sub_file, 'Subscriptions.toml'))
            
        sub_dict = {
                "Vsource.source": {
                    "Property" : "pu",
                    "Subscription ID": sub_id,
                    "Unit" : "",
                    "Subscribe" : True,
                    "Data type" : "double",
                    "Multiplier" : 1 
                }
            }
        with open(os.path.join(path_to_sub_file, 'Subscriptions.toml'), "w") as f:
            toml.dump(sub_dict, f)

        pub_dict = {
            "Circuits": {
                "Publish": ["TotalPower"],
                "NoPublish": []
            },
            "PVSystems": {
                "Publish" : [],
                "NoPublish" : ["Powers"]
            },
            "Generators": {
                "Publish" : [],
                "NoPublish" : ["Powers"]
            }
        }
        with open(os.path.join(path_to_sub_file, "ExportMode-byClass.toml"), "w") as f:
            toml.dump(pub_dict, f)
        logger.info('ExportMode-byClass.toml file changed')
        

    def update_project_params(self,params):

        """ Grab file and metadata info of case file """
        self.tmp_folder = os.path.join(os.path.dirname(__name__), '..', 'tmp')
        file_uuid = params["powerflow_options"]["pydss_project"]

        """ If folder does not exist, create a temporary folder"""
        if not os.path.exists(self.tmp_folder):
            os.mkdir(self.tmp_folder)

        folder_name = f"{params['cosim_uuid']}_{params['name']}"
        self.folder_name = folder_name
        case_file_url = f'{self.data_service_url}/case_files/uuid/{file_uuid}'

        """ Creating a project folder and removing if already exists"""
        self.project_folder = os.path.join(self.tmp_folder, folder_name)
        if not os.path.exists(self.project_folder):
            os.mkdir(self.project_folder)
        else:
            shutil.rmtree(self.project_folder)
            os.mkdir(self.project_folder)
        
        """ Retrieve the file url from the BES Data API """
        self.notify(f"URL for PYDSS case file {case_file_url}")
        file_response = send_sync_request(case_file_url, 'GET', body=None)
        file_data = json.loads(file_response.data.decode('utf-8'))

        if file_response.status == HTTPStatus.OK:
            file_url = file_data['file_url']
            self.notify(f"URL to download the file> {file_url}")
            file_format = file_data['format']

            """ Retrieve the file from AWS and store in the tmp directory """
            data_response = send_sync_request(file_url, 'GET')
            if data_response.status == HTTPStatus.OK:
                file = os.path.join(self.project_folder, f'{file_uuid}.{file_format}')
                with open(file, 'wb') as f:
                    f.write(data_response.data)

                """ Unzip the files """
                zip_path = os.path.join(self.project_folder, f'{file_uuid}.{file_format}')
                if zip_path.endswith('.zip'):
                    with ZipFile(zip_path, 'r') as zipObj:
                        zipObj.extractall(path=self.project_folder)
                    
                    os.remove(zip_path)
                
                    params['powerflow_options'].update({
                        'pydss_project' : self.project_folder,
                        'active_project' : file_data['case']['active_project'],
                        'active_scenario' : file_data['case']['active_scenario'],
                        'master_dss_file' : file_data['case']['dss_file']
                    })
                    print(params)
                    #TODO: validate pydss project skeleton

                    # Update subscriptions.toml file with sub id if sub_id exists
                    if 'sub_id' in params['powerflow_options']:
                        sub_id = params['powerflow_options'].pop('sub_id')
                        path_to_sub_file = os.path.join(self.project_folder, file_data['case']['active_project'], 
                                'Scenarios', file_data['case']['active_scenario'], 'ExportLists')

                        
                        self.update_subscription_publications_in_toml_file(sub_id, path_to_sub_file)
                        
                    
                    """ create log folder if not present """
                    log_folder  = os.path.join(self.project_folder, file_data['case']['active_project'], 'Logs')
                    if not os.path.exists(log_folder):
                        os.mkdir(log_folder)

                    return params
                else:
                    logger.error(f'PyDSS case file is not a zip file')
                    self.notify(f"PyDSS case file is not a zip file", log_level=logging.ERROR)
                    return None
            else:
                logger.error(f'Error fetching data from AWS S3')
                self.notify(f"Error fetching data from AWS S3", log_level=logging.ERROR)
                return None

        else:
            logger.error(f'Error fetching PyDSS project!')
            self.notify(f"Error fetching PyDSS project!", log_level=logging.ERROR)
            return None

    def create_substation(self, base_path, feeder_models, source_voltage):
        substation_kw = 0
        substation_kvar = 0
        master_dss_file = "master.dss"
        redirect_lines = []
        feeder_bus = []
        feeder_kv = []
        all_voltage_bases = []
        for feeder in feeder_models:
            feeder_path = os.path.join(base_path, feeder, master_dss_file)
            dss.run_command(f"compile {feeder_path}")
            dss.run_command(f"solve")
            P, Q = dss.Circuit.TotalPower()
            substation_kw += P
            substation_kvar += Q

            f = open(feeder_path, "r")
            lines = f.readlines()
            f.close()
            for line in lines:

                if "voltagebases" in line.lower():
                    redirect_lines.append(line)
                    sStrings = line.split(" ")
                    for sString in sStrings:
                        if "voltagebases=" in sString.lower():
                            vbase = sString.replace("voltagebases=", '')
                            vbase = ast.literal_eval(vbase)
                            all_voltage_bases.extend(vbase)

                if "redirect" in line.lower():
                    sStrings = line.split(" ")
                    nLine = f"redirect {feeder}/{sStrings[1]}"
                    redirect_lines.append(nLine)

                if "circuit" in line.lower():
                    sStrings = line.split(" ")
                    for sString in sStrings:
                        if "bus1" in sString.lower():
                            feeder_bus.append(sString.lower().replace("bus1", "").split(".")[0])
                        if "basekv" in sString.lower():
                            feeder_kv.append(sString.lower().replace("basekv", ""))

        master_file_path = os.path.join(base_path, master_dss_file)
        f = open(master_file_path, "w")
        f.write("clear\n")
        f.write(f"new circuit.substation basekv={source_voltage} pu=1.03 phases=3 bus1=source_bus")

        substation_kva = (substation_kw**2 + substation_kvar**2)**0.5

        tr = f"New Transformer.ABC phases=3 Windings=2 xhl=5"
        wdg1 = f" wdg=1 bus=source_bus conn=delta kV={source_voltage} kva={substation_kva} %r=0.1"
        wdg2 = f" wdg=2 bus=substation_bus conn=wye kV=12.47 kva={substation_kva} %r=0.1\n"
        f.write(tr + wdg1 + wdg2)

        for i, kv, bus in zip(range(len(feeder_kv)), feeder_kv, feeder_bus):
            f.write(f"new reactor.switch_{i} phases=3 Bus1=substation_bus Bus2={bus} R=0 X=0.000001 kv=12.47")
            assert kv == "12.47", "There is a voltage mismatch between substation and feeder models"

        for line in redirect_lines:
            f.write(line + "\n")

        f.write(f"set voltagebases={list(set(all_voltage_bases))}\n")
        f.write(f"calcvoltagebases\n")
        f.write(f"solve\n")
        f.close()
        return master_dss_file

    def update_project(self,
                       file_uuids,
                       load_mw,
                       load_mvar,
                       der_mw,
                       der_mvar,
                       source_voltage,  # @KAPIL NEED TO GET THIS INFORMATION FROM COSIM LAUNCHER
                       motor_d: 0,
                       pvcategory={"ieee-2018-catI": 0, "ieee-2018-catII": 0, "ieee-2018-catIII": 0, "ieee-2003": 0},
                       dynamic= True,
                       update_model=True,

                       ):

        """ Grab file and metadata info of case file """
        tmp_folder = os.path.join(os.path.dirname(__name__), '..', 'tmp')

        """ If folder does not exist, create a temporary folder"""
        if not os.path.exists(self.tmp_folder):
            os.mkdir(tmp_folder)

        feeder_folders = []
        for file_uuid in file_uuids:

            folder_name = file_uuid + 'distribution_federate'
            case_file_url = f'{self.data_service_url}/case_files/uuid/{file_uuid}'

            """ Creating a project folder and removing if already exists"""
            dss_dump = os.path.join(tmp_folder, folder_name)
            feeder_folders.append(folder_name)
            if not os.path.exists(dss_dump):
                os.mkdir(dss_dump)
            else:
                shutil.rmtree(dss_dump)
                os.mkdir(dss_dump)

            """ Retrieve the file url from the BES Data API """
            self.notify(f"URL for PYDSS case file {case_file_url}")
            file_response = send_sync_request(case_file_url, 'GET', body=None)
            file_data = json.loads(file_response.data.decode('utf-8'))

            if file_response.status == HTTPStatus.OK:
                file_url = file_data['file_url']
                self.notify(f"URL to download the file> {file_url}")
                file_format = file_data['format']

                """ Retrieve the file from AWS and store in the tmp directory """
                data_response = send_sync_request(file_url, 'GET')
                if data_response.status == HTTPStatus.OK:
                    file = os.path.join(dss_dump, f'{file_uuid}.{file_format}')
                    with open(file, 'wb') as f:
                        f.write(data_response.data)

                    """ Unzip the files """
                    zip_path = os.path.join(dss_dump, f'{file_uuid}.{file_format}')
                    if zip_path.endswith('.zip'):
                        with ZipFile(zip_path, 'r') as zipObj:
                            zipObj.extractall(path=dss_dump)
                        os.remove(zip_path)

                        """ create a new PyDSS project here"""

                    else:
                        logger.error(f'OpenDSS model is not a zip file')
                        self.notify(f"OpenDSS model is not a zip file", log_level=logging.ERROR)
                        return {}
                else:
                    logger.error(f'Error fetching data from AWS S3')
                    self.notify(f"Error fetching data from AWS S3", log_level=logging.ERROR)
                    return {}

            else:
                logger.error(f'Error fetching distribution models!')
                self.notify(f"Error fetching distribution models!", log_level=logging.ERROR)
                return {}


        master_file = self.create_substation(tmp_folder, feeder_folders, source_voltage)

        scenario = "scenario1"
        project = "project1"
        try:
            self.create_project(
                dss_dump,
                project,
                scenario,
                dss_dump,
                master_file, #file_data['case']['master_file']
            )

            """ update the model with new settings """
            model_modifier = PyDSS_Model(os.path.join(dss_dump, project))
            pmult, qmult = model_modifier.create_new_scenario(
                scenario,
                {
                    "Lp": load_mw,
                    "Lq": load_mvar,
                    "PVp": der_mw,
                    "PVq": der_mvar,
                    "Mtr": motor_d
                },
                {
                    "new_master": "new_" + master_file, #file_data['case']['master_file'],
                    "master": master_file, #file_data['case']['master_file'],
                    "load": 'Loads.dss',  # TODO: needs to come from metadata
                    "motor": 'Motors_new.dss',
                    "PVsystem": 'PVSystems_new.dss',
                },
                isSubstation=True,  # TODO: needs to come from metadata
                pvstandards=pvcategory,
                dynamic=True
            )

            powerflow_options = {
                'pydss_project': dss_dump,
                'active_project': project,
                'active_scenario': scenario,
                'master_dss_file': master_file, #file_data['case']['master_file']
            }


        except Exception as e:
            logger.error(f'Error updating the PyDSS project >> {e}')
            self.notify(f"Error updating the PyDSS project >> {e}", log_level=logging.ERROR)
            return {}

        # TODO: validate pydss project skeleton

        return {
            "powerflow_options": powerflow_options,
            "mw_multiplier": pmult,
            "mvar_multiplier": qmult
        }



    def create_project(self, 
        project_path,
        project_name,
        scenario_name,
        dss_path,
        master_file
        ):

        #activate pydss_api && 
        cmd = "activate pydss_api &&  pydss create-project -P {} -p {} -s {} -F {} -m {} -c {}".format(
            project_path,
            project_name,
            scenario_name,
            dss_path,
            master_file,
            "PvVoltageRideThru,MotorStall"
        )
        os.system(cmd)
        return

    def run_process(self):
        logger.info("PyDSS simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.queue.get()
                if task == 'END':
                    break
                elif "parameters" not in task:
                    result = {
                        "Status": 500,
                        "Message": "No parameters passed"
                    }
                else:
                    command = task["command"]
                    parameters = task["parameters"]
                    if hasattr(self, command):
                        func = getattr(self, command)
                        status, msg = func(parameters)
                        result = {"Status": status, "Message": msg, "UUID": self.uuid}
                    else:
                        logger.info(f"{command} is not a valid PyDSS command")
                        result = {"Status": 500, "Message": f"{command} is not a valid PyDSS command"}
                self.queue.put(result)
            
            except Empty:
                continue

            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"PyDSS subprocess {self.uuid} has ended")


    def close_instance(self):
        del self.pydss_obj
        logger.info(f'PyDSS case {self.uuid} closed.')

    def restructure_results(self, results):
        restructured_results = {}
        for k, val in results.items():
            if "." not in k:
                class_name = "Bus"
                elem_name = k
            else:
                class_name, elem_name = k.split(".")
            if class_name not in restructured_results:
                restructured_results[class_name] = {}
            if not isinstance(val, complex):
                restructured_results[class_name][elem_name] = val
            else:
                restructured_results[class_name][elem_name+'@real'] = val.real
                restructured_results[class_name][elem_name+'@imag'] = val.imag

        return restructured_results


    def run(self, params):
        if self.initalized:
            try:
                Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()

                for i in range(Steps):
                    self.notify(f"PyDSS cosim running for timestep: {i*self.time_resolution}, total timesteps: {Steps}")
                    results = self.pydss_obj.RunStep(i)
                    restructured_results = self.restructure_results(results)
                    self.notify(f"PyDSS simulation done attempting to write")
                    #Timestep data payload and metadata only in an inital timestep
                    self.a_writer.write(
                        self.parameters['name'],
                        self.pydss_obj._dssSolver.GetTotalSeconds(),
                        restructured_results,
                        i,
                        fed_uuid=self.parameters['fed_uuid'],
                        cosim_uuid=self.parameters['cosim_uuid']
                    )
                    self.notify(f"PyDSS output written for timestep : {i}")
                    
                #closing federate
                # TODO: At the moment, I cannot pass timestep because bes_data_api attemps to create a vector tile results
                self.notify(f"PyDSS attempting to close")
                self.a_writer.send_timesteps()
                self.notify(f"PyDSS closed properly")
                
                # Remove the project data
                if hasattr(self, 'tmp_folder'):
                    self.notify(f"PyDSS cleaned project folder")
                    if os.path.exists(os.path.join(self.tmp_folder, self.folder_name)):
                        shutil.rmtree(os.path.join(self.tmp_folder, self.folder_name))

                self.close_instance()
                self.notify(f"PyDSS federate successfully finalized")

                self.initalized = False
                return 200, f"Simulation complete..."
            except Exception as e:
                print(e)
                self.notify(f"Error, > {str(e)}")
                self.initalized = False
                return 500, f"Simulation crashed at at simulation time step: {self.pydss_obj._dssSolver.GetDateTime()}, {e}"
        else:
            return 500, f"No project initialized. Load a project first using the 'init' command"

    def registerPubSubs(self, params):
        subs = params["Subscriptions"]
        pubs = params["Publications"]
        self.pydss_obj._HI.registerPubSubTags(pubs, subs)
        return 200, f"Publications and subscriptions have been registered; Federate has entered execution mode"

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)
    a = PyDSS()
    del a

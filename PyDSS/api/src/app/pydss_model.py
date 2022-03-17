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
from PyDSS.api.src.app.Optimizer import Optimizer
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
logging.basicConfig(format='%(asctime)s %(message)s',level=logging.DEBUG)

def create_substation(base_path, feeder_models, source_voltage):
        
    substation_kw = 0
    substation_kvar = 0
    master_dss_file = "Master.dss"
    redirect_lines = []
    feeder_bus = []
    feeder_kv = []
    all_voltage_bases = []
    for feeder in feeder_models:
        
        feeder_path = os.path.join(base_path, feeder, master_dss_file)
        logging.info(f"Working on {feeder_path}")

        with open(feeder_path, "r") as f:
            lines = f.readlines()

        dss.run_command(f"compile {feeder_path}")
        dss.run_command(f"solve")
        P, Q = dss.Circuit.TotalPower()
        dss.run_command("clearall")
        substation_kw += P
        substation_kvar += Q

        
        for line in lines:

            if "voltagebases=" in line.lower():
                # redirect_lines.append(line)
                # sStrings = line.split(" ")
                sStrings = line.lower()
                sStrings = sStrings.split("voltagebases=")[1]
                for remove_str in ['[', ']']:
                    sStrings = sStrings.replace(remove_str, '')
                sStrings = sStrings.split(",")
                vbase = [round(float(el),3) for el in sStrings]
                all_voltage_bases.extend(vbase)
                all_voltage_bases.append(source_voltage)

                # for sString in sStrings:
                    # if "voltagebases=" in sString.lower():
                    #     sString = sString.lower()
                    #     vbase = sString.replace("voltagebases=", '')
                    #     print(vbase)
                    #     vbase = ast.literal_eval(vbase)

                

            if "redirect" in line.lower():
                sStrings = line.split(" ")
                nLine = f"redirect {feeder}/{sStrings[1]}"
                redirect_lines.append(nLine)

            if "circuit" in line.lower():
                sStrings = line.split(" ")
                for sString in sStrings:
                    if "bus1" in sString.lower():
                        feeder_bus.append(sString.lower().replace("bus1=", "").split(".")[0])
                    if "basekv" in sString.lower():
                        feeder_kv.append(sString.lower().replace("basekv=", ""))

    master_file_path = os.path.join(base_path, master_dss_file)
    f = open(master_file_path, "w")
    f.write("clear\n")
    f.write(f"new circuit.substation basekv={source_voltage} pu=1.03 phases=3 bus1=source_bus\n")

    substation_kva = (substation_kw**2 + substation_kvar**2)**0.5

    tr = f"New Transformer.ABC phases=3 Windings=2 xhl=5"
    wdg1 = f" wdg=1 bus=source_bus conn=delta kV={source_voltage} kva={substation_kva} %r=0.1"
    wdg2 = f" wdg=2 bus=substation_bus conn=wye kV=12.47 kva={substation_kva} %r=0.1\n"
    f.write(tr + wdg1 + wdg2)

    for i, kv, bus in zip(range(len(feeder_kv)), feeder_kv, feeder_bus):
        f.write(f"new reactor.switch_{i} phases=3 Bus1=substation_bus Bus2={bus} R=0 X=0.000001 kv=12.47\n")
        assert kv == "12.47", "There is a voltage mismatch between substation and feeder models"

    for line in redirect_lines:
        f.write(line + "\n")

    f.write(f"set voltagebases={list(set(all_voltage_bases))}\n")
    f.write(f"calcvoltagebases\n")
    f.write(f"solve\n")
    f.close()
    return master_dss_file

def update_project(
                    file_uuids,
                    loadflow_vpu,
                    loadflow_P,
                    loadflow_Q,
                    load_mw,
                    load_mvar,
                    der_mw,
                    der_mvar,
                    source_voltage,
                    data_service_url,  # @KAPIL NEED TO GET THIS INFORMATION FROM COSIM LAUNCHER
                    motor_d,
                    pvcategory={"ieee-2018-catI": 5, "ieee-2018-catII": 10, "ieee-2018-catIII": 15, "ieee-2003": 20},
                    dynamic= True,
                    update_model=True,
                    ):

    """ Grab file and metadata info of case file """
    tmp_folder = os.path.join(os.path.dirname(__name__), '..', 'tmp')
    pydss_model_folder = os.path.join(os.path.dirname(__name__), '..', 'tmp_pydss_project')

    """ If folder does not exist, create a temporary folder"""
    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)

    if not os.path.exists(pydss_model_folder):
        os.mkdir(pydss_model_folder)

    feeder_folders = []
    logger.info(f"Downloading {len(file_uuids)} feeders")
    
    for file_uuid in file_uuids:

        folder_name = file_uuid + '_distribution_federate'
        case_file_url = f'{data_service_url}/case_files/uuid/{file_uuid}'

        """ Creating a project folder and removing if already exists"""
        dss_dump = os.path.join(tmp_folder, folder_name)
        feeder_folders.append(folder_name)
        if not os.path.exists(dss_dump):
            os.mkdir(dss_dump)
        else:
            shutil.rmtree(dss_dump)
            os.mkdir(dss_dump)

        """ Retrieve the file url from the BES Data API """
        logger.info(f"URL for PYDSS case file {case_file_url}")
        file_response = send_sync_request(case_file_url, 'GET', body=None)
        file_data = json.loads(file_response.data.decode('utf-8'))

        if file_response.status == HTTPStatus.OK:
            file_url = file_data['file_url']
            logger.info(f"URL to download the file> {file_url}")
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
                    return {}
            else:
                logger.error(f'Error fetching data from AWS S3')
                return {}

        else:
            logger.error(f'Error fetching distribution models!')
            return {}

    tmp_folder = os.path.abspath(tmp_folder)
    pydss_model_folder = os.path.abspath(pydss_model_folder)
    master_file = create_substation(tmp_folder, feeder_folders, source_voltage)


    scenario = "scenario1"
    project = "project1"
    try:
        create_project(
            pydss_model_folder,
            project,
            scenario,
            tmp_folder,
            master_file, #file_data['case']['master_file']
        )

        """ update the model with new settings """
        project_path = os.path.join(pydss_model_folder, project)
        model_modifier = PyDSS_Model(project_path)
        new_master_file = "new_" + master_file
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
                "new_master": new_master_file, #file_data['case']['master_file'],
                "master": master_file, #file_data['case']['master_file'],
                "load": 'Loads.dss',  # TODO: needs to come from metadata
                "motor": 'Motors_new.dss',
                "PVsystem": 'PVSystems_new.dss',
                "new_loads" : 'Loads_new.dss',
            },
            isSubstation=True,  # TODO: needs to come from metadata
            PVstandards=pvcategory,
            dynamic=True
        )

        O = Optimizer(project_path, new_master_file, "test.dss")
        pmult, qmult = O.Optimize(loadflow_vpu, loadflow_P, loadflow_Q)
        print("P multiplier: ", pmult)
        print("Q multiplier: ", qmult)
        
        powerflow_options = {
            'pydss_project': pydss_model_folder,
            'active_project': project,
            'active_scenario': scenario,
            'master_dss_file': master_file, #file_data['case']['master_file']
            'master_dss_file': master_file, #file_data['case']['master_file']
        }


    except Exception as e:
        logger.error(f'Error updating the PyDSS project >> {e}')
        return {}

    # TODO: validate pydss project skeleton

    return {
        "powerflow_options": powerflow_options,
        "mw_multiplier": pmult,
        "mvar_multiplier": qmult
    }



def create_project( 
    project_path,
    project_name,
    scenario_name,
    dss_path,
    master_file
    ):

    #activate pydss_api && 
    cmd = "pydss create-project -P {} -p {} -s {} -F {} -m {} -c {}".format(
        project_path,
        project_name,
        scenario_name,
        dss_path,
        master_file,
        "PvVoltageRideThru,MotorStall"
    )
    os.system(cmd)
    return


if __name__ == '__main__':

    a = update_project(
        [
            "218672ac-d416-4e9f-8578-0d2a531aa33c",
            "41e17deb-dd30-4fdc-9265-c791677144a4",
            "d1a88f96-88ef-4c43-929c-c4d2bef283a6",
            "5c688a26-4c77-44fa-b427-bb0b0595aabf",
            "a46a7e1c-f28c-42bc-bc71-f3a8e224fbfa",
            "b9cdc11d-29d5-47e8-bdf4-30e875d95f9b",
            "315027be-b835-4d3d-8ded-53fe35ed515c",
            "2a721874-1fa2-4206-ba9b-0a377f6ab3a9",
            "b3936400-8748-4294-8256-0409b0bedaba",
            "d709b910-7f2a-4e74-b9b7-3fc7287e821b"
        ],
        1.032, 20, 3, 20, 3, 4, 0, 33, 'https://api.naerm.team/data/bes', 30,
        {"ieee-2018-catI": 5, "ieee-2018-catII": 10, "ieee-2018-catIII": 15, "ieee-2003": 20}
    )
    print(a)


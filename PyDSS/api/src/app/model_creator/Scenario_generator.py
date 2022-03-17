from PyDSS.api.src.app.model_creator.PyDSS_model_generator import ModelGenerator
from PyDSS.pydss_project import PyDssScenario
from PyDSS import defaults as PyDSS_defaults
from PyDSS.common import ControllerType
import opendssdirect as dss
import distutils.dir_util
import pandas as pd
import numpy as np
import random
import shutil
import toml
import os

class PyDSS_Model:

    motorSettings = {
        "ratedKW" : (3, 10),
        "ratedPF": (0.92, 0.97),
        "Pfault": (2.5, 3.5),
        "Vstall": (0.55, 0.6),
        "Tprotection": (10.0, 20.0),
        "Treconnect": (4.0, 8.0),

    }

    PVCategory = ['Category I', 'Category II', 'Category III', "Mix"]

    standard = ["1547-2003", "1547-2018"]

    permissive_operation = ["Current limited", "Momentary sucession"]
    may_trip_operation = ["Trip", "Permissive operation"]
    multiple_disturbances = ["Trip", "Permissive operation"]

    Category = {
        'Category I': {'OV2 - p.u.': 1.2, 'OV2 CT - sec': 0.16, 'OV1 - p.u.': 1.1, 'OV1 CT - sec': 2.0, 'UV1 - p.u.': 0.7,
                  'UV1 CT - sec': 2.0, 'UV2 - p.u.': 0.45, 'UV2 CT - sec': 0.16},

        'Category II': {'OV2 - p.u.': 1.2, 'OV2 CT - sec': 0.16, 'OV1 - p.u.': 1.1, 'OV1 CT - sec': 2.0, 'UV1 - p.u.': 0.7,
                  'UV1 CT - sec': 10.0, 'UV2 - p.u.': 0.45, 'UV2 CT - sec': 0.16},

        'Category III': {'OV2 - p.u.': 1.2, 'OV2 CT - sec': 0.16, 'OV1 - p.u.': 1.1, 'OV1 CT - sec': 13.0, 'UV1 - p.u.': 0.88,
                  'UV1 CT - sec': 21.0, 'UV2 - p.u.': 0.5, 'UV2 CT - sec': 2.0},
    }

    PVsettings = {'Category': 'test', 'kVA': 4.0, 'maxKW': 4.0, 'KvarLimit': 1.76, '%PCutin': 10.0, '%PCutout': 10.0,
                  'UcalcMode': 'Max', 'Priority': 'Equal', 'Enable PF limit': False, 'pfMin': 0.95,
                  'Follow standard': '', 'Ride-through Category': '', 'Reconnect deadtime - sec': 3000.0,
                  'Reconnect Pmax time - sec': 300.0, 'Permissive operation': '',
                  'May trip operation': '', 'Multiple disturbances': ''}

    Scenarios = ['None', 'PV', 'motorD', 'PV-MotorD']

    def __init__(self, pydssProjectPath):
        self.path = pydssProjectPath
        self.project = os.path.join(pydssProjectPath, 'Scenarios')
        self.scenarios = [f.name for f in os.scandir(self.project) if f.is_dir()]
        print('sceanrio',self.scenarios)


    def get_init_model_info(self, master_file):
        reply = dss.utils.run_command('Clear')
        dss.Basic.ClearAll()
        #try:
        orig_dir = os.getcwd()
        os.chdir(orig_dir)
        dss_path = os.path.join(self.path, "DSSfiles", master_file)
        reply = dss.utils.run_command(f'redirect {dss_path}')
        dss.Solution.Solve()
        Pl = -dss.Circuit.TotalPower()[0]
        Ql = -dss.Circuit.TotalPower()[1]
        load = dss.Loads.First()
        loads_P = []
        loads_Q = []
        while load:
            lName = dss.Loads.Name()
            phases = int(dss.utils.run_command(f"? Load.{lName}.phases"))
            if phases < 3:
                loads_P.append(dss.Loads.kW())
                loads_Q.append(dss.Loads.kvar())
            load = dss.Loads.Next()
        SPLn = len(loads_P)
        SPLn_P = sum(loads_P)
        SPLn_Q = sum(loads_Q)
        dss.utils.run_command('Clear')
        dss.Basic.ClearAll()
        return Pl/1000.0, Ql/1000.0, SPLn, SPLn_P/1000.0, SPLn_Q/1000.0

    def create_new_scenario(self, scenaio_name, transInfo, files, isSubstation, PVstandards, dynamic):
        tP, tQ, nLoads, lP, lQ = self.get_init_model_info(files["master"])
     
        self.Files = files
        penPV_P = transInfo['PVp'] / transInfo['Lp']
        penPV_Q = transInfo['PVq'] / transInfo['Lq']
        PVtP = penPV_P * tP / nLoads * 1000.0
        PVtQ = penPV_Q * tQ / nLoads * 1000.0
        mtrSize =  lP / nLoads * 1000.0
        controllers = {
          "PvVoltageRideThru": {"Penetration": penPV_P, "Size": [PVtP, PVtQ]},
          "MotorStall": {"Penetration": transInfo['Mtr'] / 100.0, "Size": mtrSize},
        }
        pubPmult = (transInfo['Lp'] - transInfo['PVp']) / (tP - penPV_P * tP) / -1000.0
        pubQmult = (transInfo['Lq'] - transInfo['PVq']) / (tQ - penPV_Q * tQ) / -1000.0
        controller_types = [ControllerType(x) for x in controllers.keys()]
        self.Scenario = PyDssScenario([scenaio_name], controller_types, export_modes=None, visualization_types=None)
        scenarioPath = os.path.join(self.project, scenaio_name)

        if os.path.exists(scenarioPath):
            shutil.rmtree(scenarioPath)
            os.mkdir(scenarioPath)

        self.Model = ModelGenerator(self.path, self.path, isSubstation)
        self.Model.GenerateScenario(
            controllers["PvVoltageRideThru"]["Penetration"],
            controllers["PvVoltageRideThru"]["Size"],
            controllers["MotorStall"]["Penetration"],
            controllers["MotorStall"]["Size"],
            files
        )

        MotorSettings = self.createMotorDict(self.Model.Motors)

        PVsystems = []
        for k, v in self.Model.PVsystems.items():
            PVsystems.extend(v)
        PVsettings = self.createPVdict(PVsystems, PVstandards)

        self.Scenario.controllers[ControllerType.PV_VOLTAGE_RIDETHROUGH] = PVsettings
        self.Scenario.controllers[ControllerType.MOTOR_STALL] = MotorSettings
        self.Scenario.serialize(scenarioPath)
        self.createPyDSStomlFile(scenaio_name)
        self.toml_to_excel(scenarioPath, False)
        return pubPmult, pubQmult

    def toml_to_excel(self, scenarioPath, remove_toml_files):
        controller_path = os.path.join(scenarioPath, "pyControllerList")
        toml_files = list(filter(lambda x: '.toml' in x, os.listdir(controller_path)))
        for toml_file in toml_files:
            toml_path = os.path.join(controller_path, toml_file)
            content = toml.load(toml_path)
            content = pd.DataFrame(content).T
            excel__path = os.path.join(controller_path, f'{toml_file.replace(".toml", "")}.xlsx')
            content.to_excel(excel__path, startrow=1)
            if remove_toml_files:
                if os.path.exists(toml_path):
                    os.remove(toml_path)
        return

    def createPyDSStomlFile(self, scenaio_name):
        defaultsPath  = PyDSS_defaults.__path__._path[0]
        settings = toml.load(os.path.join(defaultsPath, "simulation.toml"))
        project = self.path.split("\\")[-1]
        data = self.path.split("\\")[:-1]
        path = "\\".join(data)
        settings['Project']['Project Path'] = path
        settings['Project']['Active Project'] = project
        settings['Project']['Scenarios'] = [{"name": scenaio_name,"post_process_infos" : []}]
        settings['Project']['Active Scenario'] = scenaio_name
        settings['Project']['DSS File'] = self.Files["new_master"]
        with open(os.path.join(self.path, f"{scenaio_name}.toml"), "w") as f:
            toml.dump(settings, f)
        return

    def createMotorDict(self, Motors):
        allMotors = {}
        for Motor, MotorInfo in Motors.items():
            for MotorName, MotorSize in MotorInfo.items():
                MotorKW, MotorKVAR = MotorSize
                settings = {}
                for k, v in self.motorSettings.items():
                    settings[k] = random.random() * (v[1] - v[0]) + v[0]
                settings["ratedKW"] = MotorKW
                settings["ratedPF"] = MotorKW / (MotorKW**2 + MotorKVAR**2)**0.5
                allMotors[MotorName] = settings
        return allMotors

    def createPVdict(self, PVsystems, PVcategory):
        #{"ieee-2018-catI": 0, "ieee-2018-catII": 0, "ieee-2018-catIII": 0, "ieee-2003": 0},
        # print("PVsystems: ", PVsystems)
        # print("PVcategory: ", PVcategory)

        # total_pv = 0
        # for standard, penetration in PVsystems.items():
        #     total_pv += penetration
        #     PVsystems[standard] = total_pv
        

        allPVsystems = {}

        cum_cat1 = PVcategory["ieee-2018-catI"] / 100.0
        cum_cat2 = cum_cat1 + PVcategory["ieee-2018-catII"] / 100.0
        cum_cat3 = cum_cat2 + PVcategory["ieee-2018-catIII"] / 100.0
        cum_cat4 = cum_cat3 + PVcategory["ieee-2003"] / 100.0
        for PV in PVsystems:
            settings = {**self.PVsettings}
            inv_type = random.random()
            if inv_type < cum_cat3:
                settings['Follow standard'] = "1547-2018"
                if inv_type < cum_cat1:
                    PVcategory = "Category I"
                elif inv_type < cum_cat2 and inv_type >= cum_cat1:
                    PVcategory = "Category II"
                elif inv_type < cum_cat3 and inv_type >= cum_cat2:
                    PVcategory = "Category III"
                else:
                    PVcategory = "Category I"
            else:
                settings['Follow standard'] = "1547-2003"
                PVcategory = "Category I"
            if PVcategory in self.Category:
                settings.update(self.Category[PVcategory])
                settings['Ride-through Category'] = PVcategory
            elif PVcategory == "Mix":
                cat = random.randint(0, 2)
                settings.update(self.Category[self.PVCategory[cat]])
                settings['Ride-through Category'] = self.PVCategory[cat]
            PO = random.randint(0, 1)
            MT = random.randint(0, 1)
            MD = random.randint(0, 1)

            settings['Permissive operation'] = self.permissive_operation[PO]
            settings['May trip operation'] = self.may_trip_operation[MT]
            settings['Multiple disturbances'] = self.multiple_disturbances[MD]
            allPVsystems[PV] = settings
        return allPVsystems

    def remove_all_scenarios(self, models):
        for scenario in self.scenarios:
            dest = os.path.join(self.path, 'PyDSS Scenarios', scenario, "pyControllerList")
            if not os.path.exists(dest):
                raise Exception(f"Not a valid PyDSS project. Controller defination path '{dest}' does not exist")
            for root, dirs, files in os.walk(dest):
                for file in files:
                    os.remove(os.path.join(root, file))

    def create_scenarios(self, models, enable_cosim, enable_plotting):
        for project, scenario in self.projects.items():
            for m in models:
                assert (m in self.models), 'Invalid model entered'
                src = os.path.join(self.path, project, 'PyDSS Scenarios', scenario[0])
                dest = os.path.join(self.path, project, 'PyDSS Scenarios', m)
                #pathlib.Path(dest).mkdir(parents=True, exist_ok=True)
                destination = shutil.copytree(src, dest, copy_function=shutil.copy)
                control_path = os.path.join(dest, 'pyControllerList')
                backup_control_path = os.path.join(control_path, 'New folder')
                motor_path = os.path.join(control_path, 'MotorStall.xlsx')

                if m == 'None':
                    shutil.rmtree(control_path)
                    os.mkdir(control_path)
                elif m == 'PV':
                    distutils.dir_util.copy_tree(backup_control_path, control_path)
                    os.remove(motor_path)
                    shutil.rmtree(backup_control_path)
                elif m == 'motorD':
                    shutil.rmtree(backup_control_path)

                elif m == 'PV-MotorD':
                    #destination = distutils.copytree(backup_control_path, control_path, copy_function=shutil.copy)
                    distutils.dir_util.copy_tree(backup_control_path, control_path)
                    shutil.rmtree(backup_control_path)

                self.settings["Project Path"] = self.path
                self.settings["Active Project"] = project
                self.settings["Active Scenario"] = m
                self.settings["Federate name"] = 'pydss_{}_{}'.format(project.lower(), m.lower())

                if enable_cosim:
                    self.settings["Co-simulation Mode"] = True
                    self.settings["DSS File"] = "Master.dss"
                else:
                    self.settings["Co-simulation Mode"] = False
                    self.settings["DSS File"] = "Master_2.dss"

                if enable_plotting:
                    self.settings["Create dynamic plots"] = True
                else:
                    self.settings["Create dynamic plots"] = False

                toml_path= os.path.join(dest , 'PyDSS_settings.toml')
                with open(toml_path, 'w') as fp:
                    fp.write(toml.dumps(self.settings))
        return


# a = PyDSS_Model(r"C:\Users\alatif\Desktop\p1uhs1_1247")
# a.create_new_scenario(
#     "test",
#     {
#         "Lp": 20,
#         "Lq": 5,
#         "PVp": 3,
#         "PVq": 0,
#         "Mtr": 10.3
#     },
#     {
#         "new_master": "Master_new.dss",
#         "master": "Master.dss",
#         "load": 'Loads.dss',
#         "motor": 'Motors_new.dss',
#         "PVsystem": 'PVSystems_new.dss',
#     },
#     isSubstation=True,
#     PVstandard="1547-2018",
#     PVcategory="Mix"
# )
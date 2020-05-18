
import datetime
import os
import re
import shutil
import tempfile
from distutils.dir_util import copy_tree

import pandas as pd
import pytest
import subprocess
from PyDSS.common import PROJECT_TAR, PROJECT_ZIP
from PyDSS.exceptions import InvalidParameter
from PyDSS.pydss_fs_interface import PROJECT_DIRECTORIES, SCENARIOS, STORE_FILENAME
from PyDSS.pydss_project import PyDssProject, PyDssScenario, DATA_FORMAT_VERSION
from PyDSS.pydss_results import PyDssResults, PyDssScenarioResults
from tests.common import RUN_PROJECT_PATH, SCENARIO_NAME, cleanup_project


PATH = os.path.join(tempfile.gettempdir(), "pydss-projects")
EXAMPLES_path = "examples"

@pytest.fixture
def pydss_project():
    if os.path.exists(PATH):
        shutil.rmtree(PATH)
    yield
    if os.path.exists(PATH):
        shutil.rmtree(PATH)


base_projects_path = None
def copy_examples_to_temp_folder():
    #assert os.path.exists(EXAMPLES_path)
    proc = None
    base_projects_path = os.path.join(PATH, "pydss_projects")
    print(f"Temporary path: {base_projects_path}")
    os.makedirs(base_projects_path, exist_ok=True)
    assert os.path.exists(base_projects_path)
    copy_tree(EXAMPLES_path, base_projects_path)
    return base_projects_path

def test_external_interfaces_example():
    example_name = "external_interfaces/pydss_project"
    scenarios = [
        {
            'TOML': 'helics.toml',
            'file': r"external_interfaces\Helics_example\Federate_runner.bat",
        },
        {
            'TOML': 'helics_itr.toml',
            'file': r"external_interfaces\Helics_example\Federate_runner.bat",
        },
        {
            'TOML': 'simulation.toml',
            'file': r"external_interfaces\Socket_example\Run_socket_controller_example.bat",
        },
        {
            'TOML': None,
            'file': r"external_interfaces\Python_example\Run_python_example.bat",
        },
    ]
    run_example(example_name, scenarios)
    return

def test_monte_carlo_example():
    example_name = "monte_carlo"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(example_name, scenarios)
    return

def test_dynamic_visualization_example():
    example_name = "dynamic_visualization"
    scenarios = [
        {
            'TOML' : 'simulation.toml',
            'file' : None,
        },
        {
            'TOML' : 'networkgraph.toml',
            'file' : None,
        },
    ]
    run_example(example_name, scenarios)
    return

def test_custom_contols_example():
    example_name = "custom_contols"
    scenarios = [
        {
            'TOML' : 'simulation.toml',
            'file' : None,
        },
    ]
    run_example(example_name, scenarios)
    return

def test_harmonics_example():
    example_name = "harmonics"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
        {
            'TOML': 'snapshot.toml',
            'file': None,
        },
    ]
    run_example(example_name, scenarios)
    return

def run_example(example_name, scenarios):

    proc = None
    assert isinstance(example_name, str)
    assert isinstance(scenarios, list)
    base_projects_path = copy_examples_to_temp_folder()
    for S in scenarios:
        assert isinstance(S, dict)
        sim_file = S["TOML"]
        sup_file = S["file"]

        print(f'Running scenario {example_name} for example {sim_file}')
        if sup_file != None:
            sup_file_path = os.path.join(base_projects_path, sup_file)
            assert os.path.exists(sup_file_path)
            dir_path = os.path.dirname(sup_file_path)
            dir_main = os.getcwd()
            os.chdir(dir_path)
            print(dir_path)
            print(f"Running {sup_file_path} in a subprocess")
            proc = subprocess.Popen(sup_file_path, shell=True, stdout=subprocess.PIPE)
            os.chdir(dir_main)

        if sim_file:
            project_path = os.path.join(base_projects_path, example_name)
            assert os.path.exists(base_projects_path)
            PyDssProject.run_project(project_path, options=None, tar_project=False, zip_project=False,
                                     scenario=sim_file)
        print("Run complete")

        if proc != None:
            proc.terminate()
    return

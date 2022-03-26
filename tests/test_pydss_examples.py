
import os
import sys
import shutil
import tempfile
from distutils.dir_util import copy_tree

import pytest
import subprocess
from PyDSS.pydss_project import PyDssProject

import logging

logger = logging.getLogger(__name__)

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
def copy_examples_to_temp_folder(example_name):
    if "/" in example_name:
        example_name = example_name.split("/")[0]
    #assert os.path.exists(EXAMPLES_path)
    proc = None
    base_projects_path = os.path.join(PATH,example_name)
    os.makedirs(base_projects_path, exist_ok=True)
    assert os.path.exists(base_projects_path)
    copy_tree(EXAMPLES_path, base_projects_path)
    return base_projects_path

@pytest.mark.skip
def test_external_interfaces_example(pydss_project):
    example_name = "external_interfaces/pydss_project"
    scenarios = [
        {
            'TOML': 'helics.toml',
            'file': r"external_interfaces/Helics_example/run_dummy_federate.py",
        },
        {
            'TOML': 'helics_itr.toml',
            'file': r"external_interfaces/Helics_example/run_dummy_federate.py",
        },
        {
            'TOML': 'simulation.toml',
            'file': r"external_interfaces/Socket_example/run_socket_controller.py",
        },
        {
            'TOML': None,
            'file': r"external_interfaces/Python_example/run_pyDSS.py",
        },
    ]
    run_example(example_name, scenarios)
    return

def test_monte_carlo_example(pydss_project):
    example_name = "monte_carlo"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(example_name, scenarios)
    return

@pytest.mark.skip
def test_dynamic_visualization_example(pydss_project):
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

@pytest.mark.skip
def test_custom_contols_example(pydss_project):
    example_name = "custom_contols"
    scenarios = [
        {
            'TOML' : 'simulation.toml',
            'file' : None,
        },
    ]
    run_example(example_name, scenarios)
    return

@pytest.mark.skip
def test_harmonics_example(pydss_project):
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

def test_dynamics_example(pydss_project):
    example_name = "dynamics"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(example_name, scenarios)
    return

def run_example(example_name, scenarios):

    proc = None
    assert isinstance(example_name, str)
    assert isinstance(scenarios, list)
    base_projects_path = copy_examples_to_temp_folder(example_name)
    for S in scenarios:
        assert isinstance(S, dict)
        sim_file = S["TOML"]
        sup_file = S["file"]

        logger.info('Running scenario %s for example %s', example_name, sim_file)
        if sup_file != None:
            sup_file_path = os.path.join(base_projects_path, sup_file)
            assert os.path.exists(sup_file_path)
            dir_path = os.path.dirname(sup_file_path)
            dir_main = os.getcwd()
            try:
                os.chdir(dir_path)
                proc = subprocess.Popen([sys.executable, sup_file_path], shell=True)
            finally:
                os.chdir(dir_main)
        try:
            if sim_file:
                project_path = os.path.join(base_projects_path, example_name)
                assert os.path.exists(base_projects_path)
                PyDssProject.run_project(project_path, options=None, tar_project=False, zip_project=False,
                                         simulation_file=sim_file)
        finally:
            if proc != None:
                proc.terminate()
    return

#test_external_interfaces_example()

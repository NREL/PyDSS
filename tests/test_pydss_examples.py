
from distutils.dir_util import copy_tree
import subprocess
import tempfile
import logging
import signal
import shutil
import uuid
import os

import pytest

from PyDSS.pydss_project import PyDssProject

logger = logging.getLogger(__name__)

EXAMPLES_path = "examples"

@pytest.fixture
def pydss_project():
    pydss_project = tempfile.mkdtemp() 
    print(pydss_project)
    yield pydss_project
    #shutil.rmtree(pydss_project)

base_projects_path = None
def copy_examples_to_temp_folder(pydss_project, example_name):
    if "/" in example_name:
        example_name = example_name.split("/")[0]
    #assert os.path.exists(EXAMPLES_path)
    proc = None
    base_projects_path = os.path.join(pydss_project, example_name)
    os.makedirs(base_projects_path, exist_ok=True)
    assert os.path.exists(base_projects_path)
    copy_tree(EXAMPLES_path, base_projects_path)
    return base_projects_path

@pytest.mark.skip
def test_helics_interface_example(pydss_project):
    example_name = "external_interfaces/pydss_project"
    scenarios = [
        {
            'TOML': 'helics.toml',
            'file': r"external_interfaces/helics_example/run_dummy_federate.py",
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_helics_interface_iterative_example(pydss_project):
    example_name = "external_interfaces/pydss_project"
    scenarios = [
        {
            'TOML': 'helics_itr.toml',
            'file': r"external_interfaces/helics_example/run_dummy_federate.py",
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_socket_interface_example(pydss_project):
    example_name = "external_interfaces/pydss_project"
    scenarios = [
        {
            'TOML': 'socket.toml',
            'file': r"external_interfaces/socket_example/run_socket_controller.py",
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_monte_carlo_example(pydss_project):
    example_name = "monte_carlo"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(pydss_project, example_name, scenarios)
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
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_harmonics_spanshot_example(pydss_project):
    example_name = "harmonics"
    scenarios = [
        {
            'TOML': 'snapshot.toml',
            'file': None,
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_harmonics_timeseries_example(pydss_project):
    example_name = "harmonics"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

@pytest.mark.skip
def test_dynamics_example(pydss_project):
    example_name = "dynamics"
    scenarios = [
        {
            'TOML': 'simulation.toml',
            'file': None,
        },
    ]
    run_example(pydss_project, example_name, scenarios)
    return

def run_example(pydss_project, example_name, scenarios):

    proc = None
    assert isinstance(example_name, str)
    assert isinstance(scenarios, list)
    base_projects_path = copy_examples_to_temp_folder(pydss_project, example_name)
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
                proc = subprocess.Popen(["python", sup_file_path], shell=True)
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
                print("killing process")
                proc.terminate()
                # os.kill(proc.pid, signal.SIGTERM)
    return


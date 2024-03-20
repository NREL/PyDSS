from pathlib import Path

from PyDSS.common import SIMULATION_SETTINGS_FILENAME
from PyDSS.pydss_project import PyDssProject

base_path = Path(__file__).parent.absolute()

def test_voltage_ride_through():

    pydss_project = base_path / "data" / "controllers"
    project = PyDssProject.load_project(pydss_project)
    PyDssProject.run_project(
        pydss_project,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )

def test_simple_motor_stall():

    pydss_project = base_path / "data" / "controllers"
    project = PyDssProject.load_project(pydss_project)
    PyDssProject.run_project(
        pydss_project,
        simulation_file="simulation_motor_stall_simple.toml",
    )
    
def test_motor_stall():

    pydss_project = base_path / "data" / "controllers"
    project = PyDssProject.load_project(pydss_project)
    PyDssProject.run_project(
        pydss_project,
        simulation_file="simulation_motor_stall.toml",
    )
    
def test_pv_controller():

    pydss_project = base_path / "data" / "controllers"
    project = PyDssProject.load_project(pydss_project)
    PyDssProject.run_project(
        pydss_project,
        simulation_file="simulation_pv_controller.toml",
    )
from pathlib import Path
import toml
import click
import os

from PyDSS.simulation_input_models import MappedControllers
from PyDSS.pydss_project import PyDssScenario
from PyDSS.common import CONTROLLER_TYPES, ControllerType

def build_scenario(project_path:str, scenario_name:str, controller_mapping:str):
    project_path = Path(project_path)
    controller_mapping_path = Path(controller_mapping)    
    assert project_path.exists(), "Provided project path does not exist"
    assert (project_path / "Scenarios").exists(), "provided project is not a valid PyDSS project"
    assert controller_mapping_path.exists(), "rovided controller_mapping file does not exist"
    assert controller_mapping_path.suffix.lower() == ".toml", "controller_mapping should be a TOML file"
    
    controller_map = toml.load(controller_mapping_path)
    mapped_controllers = MappedControllers(**controller_map)
    acceptable_controller_types = CONTROLLER_TYPES
    controllers = {}
    for controller in mapped_controllers.mapping:
        settings_path_obj = Path(controller.controller_file)
        assert controller.controller_type in ControllerType, \
        f"{controller.controller_type} is not a valid contoller. Options are {acceptable_controller_types}"
        assert settings_path_obj.exists(), \
            f"file for controller type {controller.controller_type} does not exist"
        controller_data = toml.load(settings_path_obj)
        if controller_data:
            if controller.controller_type in controllers:
                msg= f"Multiple keys files for the same controller type {controller.controller_type}." \
                "Each controller type can only be attached to a single file."
                raise ValueError(msg)
            controllers[controller.controller_type] = toml.load(settings_path_obj)
    scenario_dir = project_path / "Scenarios" / scenario_name
    scenario_obj = PyDssScenario(
            [scenario_name], controllers=controllers, export_modes=None, visualization_types=None
        )
    scenario_obj.serialize(str(scenario_dir))

@click.argument("project-path", type=click.Path(exists=True))
@click.option(
    "-s", "--scenario_name",
    required=True,
    help="name of the new scenario",
)
@click.option(
    "-c", "--controller-mapping",
    required=True,
    default=None,
    type=click.Path(exists=True),
    help="JSON file that maps controller type to controller definition files",
)
@click.command()
def add_scenario(project_path:str, scenario_name:str, controller_mapping:str):
    """Add a new scenario to an existing project"""
    build_scenario(project_path, scenario_name, controller_mapping)


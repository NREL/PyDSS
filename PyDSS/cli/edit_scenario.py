"""CLI to edit an existing project or scenario"""

import os
import sys

import click

from PyDSS.common import ControllerType, CONTROLLER_TYPES, SIMULATION_SETTINGS_FILENAME
from PyDSS.pydss_project import ControllerType
from PyDSS.utils.dss_utils import read_pv_systems_from_dss_file
from PyDSS.registry import Registry
from PyDSS.utils.utils import dump_data, load_data


READ_CONTROLLER_FUNCTIONS = {
    ControllerType.PV_CONTROLLER.value: read_pv_systems_from_dss_file,
}


@click.option(
    "-p", "--project-path",
    required=True,
    help="project path",
)
@click.option(
    "-s", "--scenario",
    required=True,
    help="Project name (should exist)",
)
@click.group()
def edit_scenario(project_path=None, scenario=None):
    """Edit scenario in a PyDSS project."""


@click.option(
    "-c", "--controller",
    required=True,
    help="controller name",
)
@click.option(
    "-f", "--dss-file",
    required=True,
    help="OpenDSS file containing elements",
)
@click.option(
    "-t", "--controller-type",
    required=True,
    type=click.Choice(CONTROLLER_TYPES),
    help="controller type",
)
@click.command()
@click.pass_context
def update_controllers(ctx, controller_type=None, controller=None, dss_file=None):
    """Update a scenario's controllers from an OpenDSS file."""
    project_path = ctx.parent.params["project_path"]
    scenario = ctx.parent.params["scenario"]
    if controller_type not in READ_CONTROLLER_FUNCTIONS:
        supported_types = list(READ_CONTROLLER_FUNCTIONS.keys())
        print(f"Currently only {supported_types} types are supported")
        sys.exit(1)

    sim_file = os.path.join(project_path, SIMULATION_SETTINGS_FILENAME)
    config = load_data(sim_file)
    if not config["Project"].get("Use Controller Registry", False):
        print(f"'Use Controller Registry' must be set to true in {sim_file}")
        sys.exit(1)

    registry = Registry()
    if not registry.is_controller_registered(controller_type, controller):
        print(f"{controller_type} / {controller} is not registered")
        sys.exit(1)

    data = {}
    filename = f"{project_path}/Scenarios/{scenario}/pyControllerList/{controller_type}.toml"
    if os.path.exists(filename):
        data = load_data(filename)
        for val in data.values():
            if not isinstance(val, list):
                print(f"{filename} has an invalid format")
                sys.exit(1)

    element_names = READ_CONTROLLER_FUNCTIONS[controller_type](dss_file)
    num_added = 0
    if controller in data:
        existing = set(data[controller])
        final = list(existing.union(set(element_names)))
        data[controller] = final
        num_added = len(final) - len(existing)
    else:
        data[controller] = element_names
        num_added = len(element_names)

    dump_data(data, filename)
    print(f"Added {num_added} names to {filename}")


edit_scenario.add_command(update_controllers)

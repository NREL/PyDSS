"""CLI to edit an existing project or scenario"""

import click

from pydss.common import CONTROLLER_TYPES
from pydss.pydss_project import update_pydss_controllers


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
    """Edit scenario in a pydss project."""


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
    update_pydss_controllers(
        project_path=project_path,
        scenario=scenario,
        controller_type=controller_type,
        controller=controller,
        dss_file=dss_file
    )


edit_scenario.add_command(update_controllers)

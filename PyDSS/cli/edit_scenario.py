"""CLI to edit an existing project or scenario"""

import ast
import click
import logging

from PyDSS.loggers import setup_logging
from PyDSS.pydss_project import PyDssProject, PyDssScenario, ControllerType, ExportMode, VisualizationType



@click.option(
    "-P", "--path",
    required=True,
    help="Path where project exists",
)
@click.option(
    "-p", "--project",
    required=True,
    help="project name",
)
@click.option(
    "-s", "--scenario",
    required=True,
    help="Project name (should exist)",
)

@click.command()
def edit_scenario(path=None, project=None, scenarios=None):
    """edit PyDSS project."""
    print('The scenario edit feature not available. Will be available in future releases')
    return

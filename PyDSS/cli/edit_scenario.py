"""CLI to create a new PyDSS project"""

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
    """Create PyDSS project."""
    setup_logging("PyDSS", console_level=logging.INFO)
    if controller_types is not None:
        controller_types = [ControllerType(x) for x in controller_types.split(",")]
    if export_modes is not None:
        export_modes = [ExportMode(x) for x in export_modes.split(",")]
    if visualization_types is not None:
        visualization_types = [VisualizationType(x) for x in visualization_types.split(",")]

    if options is not None:
        options = ast.literal_eval(options)
        if not isinstance(options, dict):
            print(f"options must be of type dict; received {type(options)}")
            sys.exit(1)

    scenarios = [
        PyDssScenario(
            name=x.strip(),
            controller_types=controller_types,
            export_modes=export_modes,
            visualization_types=visualization_types,
        ) for x in scenarios.split(",")
    ]
    PyDssProject.create_project(
        path,
        project,
        scenarios,
        simulation_config,
        options=options
    )

"""CLI to create a new pydss project"""

import click
import ast
import sys

from loguru import logger

from pydss.pydss_project import PyDssProject, PyDssScenario, ControllerType, ExportMode


@click.option(
    "-P", "--path",
    required=True,
    help="path in which to create project",
)
@click.option(
    "-p", "--project",
    required=True,
    help="project name",
)
@click.option(
    "-s", "--scenarios",
    required=True,
    help="comma-delimited scenario names",
)
@click.option(
    "-f", "--simulation-file",
    required=False,
    show_default=True,
    default="simulation.toml",
    help="simulation file name",
)
@click.option(
    "-F", "--opendss-project-folder",
    default=None,
    required=False,
    type=click.Path(exists=True),
    help="simulation file name",
)
@click.option(
    "-m", "--master-dss-file",
    required=False,
    show_default=True,
    default=None,
    help="simulation file name",
)
@click.option(
    "-S", "--simulation-config",
    default=None,
    type=click.Path(exists=True),
    help="simulation configuration settings",
)
@click.option(
    "-c", "--controller-types",
    default=None,
    help="comma-delimited list of controller types",
)
@click.option(
    "-e", "--export-modes",
    default=None,
    help="comma-delimited list of export modes",
)
@click.option(
    "-o", "--options",
    help="dict-formatted simulation settings that override the config file. " \
         "Example:  pydss run ./project --options \"{\\\"Simulation Type\\\": \\\"QSTS\\\"}\"",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite directory if it already exists.",
)
@click.command()
def create_project(path=None, project=None, scenarios=None, simulation_file=None, simulation_config=None,
                   controller_types=None, export_modes=None, options=None, 
                   opendss_project_folder=None, master_dss_file=None, force=False):
    """Create pydss project."""
    if controller_types is not None:
        controller_types = [ControllerType(x) for x in controller_types.split(",")]
    if export_modes is not None:
        export_modes = [ExportMode(x) for x in export_modes.split(",")]
        
    if options is not None:
        options = ast.literal_eval(options)
        if not isinstance(options, dict):
            logger.error(f"options must be of type dict; received {type(options)}")
            sys.exit(1)

    scenarios = [
        PyDssScenario(
            name=x.strip(),
            controller_types=controller_types,
            export_modes=export_modes,

        ) for x in scenarios.split(",")
    ]
    PyDssProject.create_project(
        path,
        project,
        scenarios,
        simulation_config,
        options=options,
        simulation_file=simulation_file,
        master_dss_file=master_dss_file,
        opendss_project_folder = opendss_project_folder,
        force=force,
    )

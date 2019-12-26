"""CLI to create a new PyDSS project"""

import click

from PyDSS.pydss_project import PyDssProject, PyDssScenario, ControllerType, ExportMode


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
@click.command()
def create_project(path=None, project=None, scenarios=None, simulation_config=None, controller_types=None, export_modes=None):
    """Create PyDSS project."""
    if controller_types is not None:
        controller_types = [ControllerType(x) for x in controller_types.split(",")]
    if export_modes is not None:
        export_modes = [ExportMode(x) for x in export_modes.split(",")]

    scenarios = [
        PyDssScenario(
            x.strip(),
            controller_types=controller_types,
            export_modes=export_modes,
        ) for x in scenarios.split(",")
    ]
    PyDssProject.create_project(path, project, scenarios, simulation_config)

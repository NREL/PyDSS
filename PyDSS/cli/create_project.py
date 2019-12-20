"""
CLI to create a new PyDSS project
"""

import click

from PyDSS.pydss_project import PyDssProject, PyDssScenario


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
@click.command()
def create_project(path, project, scenarios, simulation_config=None):
    """Create PyDSS project."""
    scenarios = [PyDssScenario(x.strip()) for x in scenarios.split(",")]
    PyDssProject.create_project(path, project, scenarios, simulation_config)

"""
CLI to create a new PyDSS project
"""

import click

from PyDSS.pydss_project import PyDssProject


@click.argument(
    "project-path",
)
@click.command()
def run(project_path):
    """Run a PyDSS simulation."""
    PyDssProject.run_project(project_path)

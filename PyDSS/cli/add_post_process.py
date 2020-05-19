"""CLI to create a new PyDSS project"""

import ast
import click
import logging

from PyDSS.pydss_project import PyDssProject, PyDssScenario, ControllerType, ExportMode
from PyDSS.loggers import setup_logging


@click.argument("config-file")
@click.argument("script")
@click.argument("scenario-name")
@click.argument("project-path")
@click.command()
def add_post_process(project_path, scenario_name, script, config_file):
    """Add post-process script to PyDSS scenario."""
    setup_logging("PyDSS", console_level=logging.INFO)
    project = PyDssProject.load_project(project_path)
    scenario = project.get_scenario(scenario_name)
    pp_info = {"script": script, "config_file": config_file}
    scenario.add_post_process(pp_info)
    project.serialize()

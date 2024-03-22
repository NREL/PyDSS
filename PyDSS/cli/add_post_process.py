"""CLI to create a new pydss project"""


import click

from pydss.pydss_project import PyDssProject


@click.argument("config-file")
@click.argument("script")
@click.argument("scenario-name")
@click.argument("project-path")
@click.command()
def add_post_process(project_path, scenario_name, script, config_file):
    """Add post-process script to pydss scenario."""
    project = PyDssProject.load_project(project_path)
    scenario = project.get_scenario(scenario_name)
    pp_info = {"script": script, "config_file": config_file}
    scenario.add_post_process(pp_info)
    project.serialize()

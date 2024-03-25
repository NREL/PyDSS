"""Main CLI command for pydss."""

from loguru import logger
import click

from pydss.cli.create_project import create_project
from pydss.cli.add_post_process import add_post_process
from pydss.cli.controllers import controllers
from pydss.cli.convert import convert
from pydss.cli.export import export
from pydss.cli.extract import extract, extract_element_files
from pydss.cli.run import run
from pydss.cli.edit_scenario import edit_scenario

from pydss.cli.reports import reports
from pydss.cli.add_scenario import add_scenario

server_dependencies_installed = True

try:
    from pydss.cli.run_server import serve
except ImportError:
    server_dependencies_installed = False
    logger.warning(
        "Server dependencies not installed. Use 'pip install NREL-pydss[server]' to install additional dependencies"
    )

@click.group()
def cli():
    """Pydss commands"""

cli.add_command(create_project)
cli.add_command(add_post_process)
cli.add_command(export)
cli.add_command(extract)
cli.add_command(extract_element_files)
cli.add_command(run)
cli.add_command(add_scenario)
cli.add_command(edit_scenario)
cli.add_command(convert)
cli.add_command(controllers)
cli.add_command(reports)
if server_dependencies_installed:
    cli.add_command(serve)
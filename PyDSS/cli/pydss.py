"""Main CLI command for PyDSS."""

import logging


import click

from PyDSS.cli.create_project import create_project
from PyDSS.cli.add_post_process import add_post_process
from PyDSS.cli.controllers import controllers
from PyDSS.cli.convert import convert
from PyDSS.cli.export import export
from PyDSS.cli.extract import extract, extract_element_files
from PyDSS.cli.run import run
from PyDSS.cli.edit_scenario import edit_scenario
from PyDSS.cli.run_server import serve
from PyDSS.cli.reports import reports

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PyDSS commands"""

cli.add_command(create_project)
cli.add_command(add_post_process)
cli.add_command(export)
cli.add_command(extract)
cli.add_command(extract_element_files)
cli.add_command(run)
cli.add_command(edit_scenario)
cli.add_command(convert)
cli.add_command(controllers)
cli.add_command(serve)
cli.add_command(reports)

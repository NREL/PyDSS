"""Main CLI command for PyDSS."""

import logging


import click

from PyDSS.cli.create_project import create_project
from PyDSS.cli.add_post_process import add_post_process
from PyDSS.cli.excel_to_toml import excel_to_toml
from PyDSS.cli.run import run


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PyDSS commands"""


cli.add_command(create_project)
cli.add_command(add_post_process)
cli.add_command(excel_to_toml)
cli.add_command(run)

"""Main CLI command for PyDSS."""

import logging


import click

from PyDSS.cli.create_project import create_project
from PyDSS.cli.run import run


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PyDSS commands"""


cli.add_command(create_project)
cli.add_command(run)

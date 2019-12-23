"""CLI to create a TOML file from a PyDSS Excel configuration file"""

import click

from PyDSS.config_data import convert_config_data_to_toml


@click.argument(
    "filenames",
    nargs=-1,
)
@click.option(
    "-n", "--name",
    help="new filename; default is to use the basename of the XLSX file",
)
@click.command()
def excel_to_toml(filenames, name=None):
    """Convert an Excel configuration file to TOML."""
    for filename in filenames:
        convert_config_data_to_toml(filename, name)

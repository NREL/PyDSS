"""CLI to convert legacy formats"""

import os

import click

from pydss.config_data import convert_config_data_to_toml
from pydss.export_list_reader import ExportListReader
from pydss.utils.utils import dump_data


@click.group("convert")
def convert():
    """Convert input files to new formats."""


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


@click.argument(
    "filenames",
    nargs=-1,
)
@click.option(
    "-n", "--name",
    help="new filename; default is Exports.toml",
)
@click.command()
def simulation_file(filenames, name=None):
    """Convert a legacy simulation TOML file to the new format."""
    for filename in filenames:
        dirname = os.path.dirname(filename)
        if name is None:
            new_filename = os.path.join(dirname, "Exports.toml")
        else:
            new_filename = name
        reader = ExportListReader(filename)
        dump_data(reader.serialize(), new_filename)
        print(f"Converted {filename} to {new_filename}")


convert.add_command(excel_to_toml)
convert.add_command(simulation_file)

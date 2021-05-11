"""
CLI to export data from a PyDSS project
"""

import logging
import os
import sys

import click

from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from PyDSS.loggers import setup_logging
from PyDSS.utils.utils import get_cli_string


logger = logging.getLogger(__name__)

# TODO Make command to list scenarios.

@click.argument(
    "project-path",
)
@click.option(
    "-f", "--fmt",
    default="csv",
    help="Output file format (csv or h5)."
)
@click.option(
    "-c", "--compress",
    is_flag=True,
    default=False,
    show_default=True,
    help="Compress output files.",
)
@click.option(
    "-o", "--output-dir",
    help="Output directory. Default is project exports directory.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def export(project_path, fmt="csv", compress=False, output_dir=None, verbose=False):
    """Export data from a PyDSS project."""
    if not os.path.exists(project_path):
        sys.exit(1)

    filename = "pydss_export.log"
    console_level = logging.INFO
    file_level = logging.INFO
    if verbose:
        console_level = logging.DEBUG
        file_level = logging.DEBUG

    setup_logging(
        "PyDSS",
        filename=filename,
        console_level=console_level,
        file_level=file_level,
    )
    logger.info("CLI: [%s]", get_cli_string())

    results = PyDssResults(project_path)
    for scenario in results.scenarios:
        scenario.export_data(output_dir, fmt=fmt, compress=compress)

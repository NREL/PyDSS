"""
CLI to export data from a pydss project
"""

import sys
import os

from loguru import logger
import click


from pydss.pydss_results import PyDssResults
from pydss.utils.utils import get_cli_string


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
    """Export data from a pydss project."""
    if not os.path.exists(project_path):
        sys.exit(1)

    filename = "pydss_export.log"
    console_level = "INFO"
    file_level = "INFO"
    if verbose:
        console_level = "DEBUG"
        file_level = "DEBUG"

    logger.level(console_level)
    if filename:
        logger.add(filename)

    logger.info("CLI: [%s]", get_cli_string())

    results = PyDssResults(project_path)
    for scenario in results.scenarios:
        scenario.export_data(output_dir, fmt=fmt, compress=compress)

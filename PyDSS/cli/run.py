"""
CLI to create a new PyDSS project
"""

import ast
import logging
import os
import sys

import click

from PyDSS.pydss_project import PyDssProject
from PyDSS.loggers import setup_logging
from PyDSS.utils.utils import get_cli_string


logger = logging.getLogger(__name__)


@click.argument(
    "project-path",
)
@click.option(
    "-o", "--options",
    help="dict-formatted simulation settings that override the config file. " \
         "Example:  pydss run ./project --options \"{\\\"Export Iteration Order\\\": \\\"ElementValuesPerProperty\\\"}\"",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def run(project_path, options=None, verbose=False):
    """Run a PyDSS simulation."""
    if not os.path.exists(project_path):
        print(f"project-path={project_path} does not exist")
        sys.exit(1)

    config = PyDssProject.load_simulation_config(project_path)
    if verbose:
        # Override the config file.
        config['Logging Level'] = logging.DEBUG

    filename = None
    console_level = logging.INFO
    file_level = logging.INFO
    if not config["Display on screen"]:
        console_level = logging.ERROR
    if verbose:
        console_level = logging.DEBUG
        file_level = logging.DEBUG
    if config["Log to external file"]:
        logs_path = os.path.join(project_path, "Logs")
        filename = os.path.join(
            logs_path,
            os.path.basename(project_path) + ".log",
        )

    setup_logging(
        "PyDSS",
        filename=filename,
        console_level=console_level,
        file_level=file_level,
    )
    logger.info("CLI: [%s]", get_cli_string())

    if options is not None:
        options = ast.literal_eval(options)
        if not isinstance(options, dict):
            print(f"options must be of type dict; received {type(options)}")
            sys.exit(1)

    PyDssProject.run_project(project_path, options=options)

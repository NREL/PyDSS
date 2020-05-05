"""
CLI to run a PyDSS project
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
            "Example:  pydss run ./project --options \"{\\\"Exports\\\": {\\\"Export Compression\\\": \\\"true\\\"}}\"",
)
@click.option(
    "-t", "--tar-project",
    is_flag=True,
    default=False,
    show_default=True,
    help="Tar project files after successful execution."
)
@click.option(
    "-z", "--zip-project",
    is_flag=True,
    default=False,
    show_default=True,
    help="Zip project files after successful execution."
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def run(project_path, options=None, tar_project=False, zip_project=False, verbose=False):
    """Run a PyDSS simulation."""
    if not os.path.exists(project_path):
        print(f"project-path={project_path} does not exist")
        sys.exit(1)

    config = PyDssProject.load_simulation_config(project_path)
    if verbose:
        # Override the config file.
        config["Logging"]["Logging Level"] = logging.DEBUG

    filename = None
    console_level = logging.INFO
    file_level = logging.INFO
    if not config["Logging"]["Display on screen"]:
        console_level = logging.ERROR
    if verbose:
        console_level = logging.DEBUG
        file_level = logging.DEBUG
    if config["Logging"]["Log to external file"]:
        logs_path = os.path.join(project_path, "Logs")
        filename = os.path.join(
            logs_path,
            os.path.basename(project_path) + ".log",
        )

    if not os.path.exists(logs_path):
        print("Logs path does not exist. 'run' is not supported on a tarred project.")
        sys.exit(1)

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

    PyDssProject.run_project(project_path, options=options, tar_project=tar_project, zip_project=zip_project)

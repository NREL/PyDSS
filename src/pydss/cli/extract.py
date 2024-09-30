"""
CLI to extract files from an archived pydss project.
"""

import sys
import os

from loguru import logger
import click

from pydss.pydss_project import PyDssProject
from pydss.pydss_results import PyDssResults
from pydss.utils.utils import get_cli_string

@click.argument(
    "file-path",
)
@click.argument(
    "project-path",
)
@click.option(
    "-o", "--output-dir",
    help="Output directory. Default is the project path.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def extract(project_path, file_path, output_dir=None, verbose=False):
    """Extract a file from an archived pydss project."""
    if not os.path.exists(project_path):
        logger.error(f"project-path={project_path} does not exist")
        sys.exit(1)

    filename = "pydss_extract.log"
    console_level = "INFO"
    file_level = "INFO"
    if verbose:
        console_level = "DEBUG"
        file_level = "DEBUG"

    logger.level(console_level)
    if filename:
        logger.add(filename)
  
    logger.info("CLI: [%s]", get_cli_string())

    project = PyDssProject.load_project(project_path)
    data = project.fs_interface.read_file(file_path)

    if output_dir is None:
        path = os.path.join(project_path, file_path)
    else:
        path = os.path.join(output_dir, file_path)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(file_path)[1]
    mode = "wb" if ext == ".h5" else "w"
    with open(path, mode) as f_out:
        f_out.write(data)

    logger.info(f"Extracted {file_path} to {path}")


@click.argument(
    "project-path",
)
@click.option(
    "-o", "--output-dir",
    help="Output directory. Default is the project path.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable verbose log output."
)
@click.command()
def extract_element_files(project_path, output_dir=None, verbose=False):
    """Extract the element info files from an archived pydss project."""
    if not os.path.exists(project_path):
        logger.error(f"project-path={project_path} does not exist")
        sys.exit(1)

    filename = "pydss_extract.log"
    console_level = "INFO"
    file_level = "INFO"
    if verbose:
        console_level = "DEBUG"
        file_level = "DEBUG"

    logger.level(console_level)
    if filename:
        logger.add(filename)
    
    logger.info("CLI: [%s]", get_cli_string())

    project = PyDssProject.load_project(project_path)
    fs_intf = project.fs_interface
    results = PyDssResults(project_path)
    for scenario in results.scenarios:
        for filename in scenario.list_element_info_files():
            text = fs_intf.read_file(filename)

            if output_dir is None:
                path = os.path.join(project_path, filename)
            else:
                path = os.path.join(output_dir, filename)

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f_out:
                f_out.write(text)

            logger.info(f"Extracted {filename} to {path}")

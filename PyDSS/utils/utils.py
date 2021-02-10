"""Utility functions for the jade package."""

from datetime import datetime
import gzip
import logging
import json
import os
import shutil
import sys
import yaml

import opendssdirect as dss
import toml

from PyDSS.exceptions import InvalidParameter

MAX_PATH_LENGTH = 255
DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f' # '%Y-%m-%d %H:%M:%S.%f', "%m/%d/%Y %H:%M:%S"

logger = logging.getLogger(__name__)


def check_redirect(file_name):
    """Runs redirect command for dss file
    And checks for exception

    Parameters
    ----------
    file_name : str
        dss file to be redirected

    Raises
    -------
    Exception
        Raised if the command fails

    """
    logger.debug(f"Redirecting DSS file: {file_name}")
    result = dss.run_command(f"Redirect {file_name}")
    if result != "":
        raise Exception(f"Redirect failed for {file_name}, message: {result}")


def _get_module_from_extension(filename, **kwargs):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".json":
        mod = json
    elif ext == ".toml":
        mod = toml
    elif ext in (".yml", ".yaml"):
        mod = yaml
    elif "mod" in kwargs:
        mod = kwargs["mod"]
    else:
        raise InvalidParameter(f"Unsupported extension {filename}")

    return mod


def dump_data(data, filename, **kwargs):
    """Dump data to the filename.
    Supports JSON, TOML, YAML, or custom via kwargs.

    Parameters
    ----------
    data : dict
        data to dump
    filename : str
        file to create or overwrite

    """
    mod = _get_module_from_extension(filename, **kwargs)
    with open(filename, "w") as f_out:
        mod.dump(data, f_out, **kwargs)

    logger.debug("Dumped data to %s", filename)


def load_data(filename, **kwargs):
    """Load data from the file.
    Supports JSON, TOML, YAML, or custom via kwargs.

    Parameters
    ----------
    filename : str

    Returns
    -------
    dict

    """
    # TODO:  YAMLLoadWarning: calling yaml.load() without Loader=... is deprecated,
    #  as the default Loader is unsafe. Please read https://msg.pyyaml.org/load for full details.
    mod = _get_module_from_extension(filename, **kwargs)
    with open(filename) as f_in:
        data = mod.load(f_in)

    logger.debug("Loaded data from %s", filename)
    return data


def get_cli_string():
    """Return the command-line arguments issued.

    Returns
    -------
    str

    """
    return os.path.basename(sys.argv[0]) + " " + " ".join(sys.argv[1:])


def decompress_file(filename):
    """Decompress a file.

    Parameters
    ----------
    filename : str

    Returns
    -------
    str
        Returns the new filename.

    """
    assert os.path.splitext(filename)[1] == ".gz"

    new_filename = filename[:-3]
    with open(new_filename, "wb") as f_out:
        with gzip.open(filename, "rb") as f_in:
            shutil.copyfileobj(f_in, f_out)

    os.remove(filename)
    logger.debug("Decompressed %s", new_filename)
    return new_filename


def interpret_datetime(timestamp):
    """Return a datetime object from a timestamp string.

    Parameters
    ----------
    timestamp : str

    Returns
    -------
    datetime.datetime

    """
    formats = (
        "%Y-%m-%d_%H:%M:%S.%f",
        "%Y-%m-%d_%H-%M-%S-%f",
        DATE_FORMAT,
    )

    for i, fmt in enumerate(formats):
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            if i == len(formats) - 1:
                raise
            continue


def iter_elements(element_class, element_func):
    """Yield the return of element_func for each element of type element_class.

    Parameters
    ----------
    element_class : class
        Subclass of opendssdirect.CktElement
    element_func : function
        Function to run on each element

    Yields
    ------
    Return of element_func

    Examples
    --------
    >>> import opendssdirect as dss

    >>> def get_reg_control_info():
        return {
            "name": dss.RegControls.Name(),
            "enabled": dss.CktElement.Enabled(),
            "transformer": dss.RegControls.Transformer(),
        }

    >>> for reg_control in iter_elements(opendssdirect.RegControls, get_reg_control_info):
        print(reg_control["name"])
        
    """
    element_class.First()
    for _ in range(element_class.Count()):
        yield element_func()
        element_class.Next()


def make_human_readable_size(size, decimals=2):
    """Convert bytes to human readable representation.

    Parameters
    ----------
    size : float
        Size in bytes.
    decimals : int, optional
        the decimal places, by default 2

    Returns
    -------
    str:
        Human reable size string with unit.
    """
    for unit in ["B","KB","MB","GB","TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimals}f} {unit}"

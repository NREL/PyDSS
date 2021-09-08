
import logging
import re

import opendssdirect as dss

from PyDSS.exceptions import InvalidConfiguration
from PyDSS.utils.utils import iter_elements


logger = logging.getLogger(__name__)


def read_pv_systems_from_dss_file(filename):
    """Return PVSystem names specified in OpenDSS deployment file.

    Parameters
    ----------
    filename : str

    Returns
    -------
    list

    """
    pv_systems = []
    """
    New PVSystem.pv_1114018 bus1=133294_xfmr.1.2 phases=2
    """
    regex = re.compile(r"New (PVSystem\.)([\S]+)\s", re.I)

    with open(filename) as fp_in:
        for line in fp_in:
            match = regex.search(line)
            if match:
                pv_systems.append(match.group(1) + match.group(2).lower())

    logger.debug("Found pv_systems=%s in %s", pv_systems, filename)
    return pv_systems


def get_load_shape_resolution_secs():
    def func():
        if dss.LoadShape.Name() == "default":
            return None
        return dss.LoadShape.SInterval()

    res = [x for x in iter_elements(dss.LoadShape, func) if x is not None]
    if len(set(res)) != 1:
        raise InvalidConfiguration(
            f"SInterval for all LoadShapes must be the same: {res}"
        )
    return res[0]


def get_node_names_by_type(kv_base_threshold=1.0):
    """Return a mapping of node type to node names.

    Parameters
    ----------
    kv_base_threshold : float
        Voltage to use as threshold for identifying primary vs secondary

    Returns
    -------
    dict
        keys are "primaries" or "secondaries"
        values are a list of node names

    """
    names_by_type = {"primaries": [], "secondaries": []}
    for i, name in enumerate(dss.Circuit.AllNodeNames()):
        dss.Circuit.SetActiveBus(name)
        kv_base = dss.Bus.kVBase()
        if kv_base > kv_base_threshold:
            names_by_type["primaries"].append(name)
        else:
            names_by_type["secondaries"].append(name)

    return names_by_type

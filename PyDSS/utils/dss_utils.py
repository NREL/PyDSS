
import logging
import re


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
    regex = re.compile(r"New (PVSystem\.\w+)\s", re.I)

    with open(filename) as fp_in:
        for line in fp_in:
            match = regex.search(line)
            if match:
                pv_systems.append(match.group(1))

    logger.debug("Found pv_systems=%s in %s", pv_systems, filename)
    return pv_systems

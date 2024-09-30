import opendssdirect as dss

from pydss.dssTransformer import dssTransformer
from pydss.dssElement import dssElement


def create_dss_element(element_class, element_name, dss_instance=None):
    """Instantiate the correct class for the given element_class and element_name."""
    if dss_instance is None:
        dss_instance = dss
    if element_class == "Transformer":
        return dssTransformer(dss_instance)
    else:
        return dssElement(dss_instance)

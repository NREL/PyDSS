class PlotAbstract:
    """An abstract class that serves as template for all pyPlot classes in :mod:`PyDSS.pyPlots.Plots` module.

    :param PlotProperties: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type PlotProperties: dict
    :param dssBuses: Dictionary of all :class:`PyDSS.dssBus.dssBus` objects in PyDSS
    :type dssBuses: dict of :class:`PyDSS.dssBus.dssBus` objects
    :param dssObjects: Dictionary of all :class:`PyDSS.dssElement.dssElement` objects in PyDSS
    :type dssObjects: dict of :class:`PyDSS.dssElement.dssElement` objects
    :param dssCircuit:  Dictionary of all :class:`PyDSS.dssCircuit.dssCircuit` objects in PyDSS
    :type dssCircuit: dict of :class:`PyDSS.dssCircuit.dssCircuit` objects
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`

    """

    def __init__(self, PlotProperties, dssBuses, dssObjects, dssCircuit, dssSolver):
        """This is the constructor class.
        """

    def GetSessionID(self):
        return

    def UpdatePlot(self):
        """Method used to update the dynamic plots.
        """
        pass


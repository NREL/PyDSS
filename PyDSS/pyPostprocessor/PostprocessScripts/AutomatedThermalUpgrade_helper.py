from  PyDSS.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess

class AutomatedThermalUpgrade_helper(AbstractPostprocess):
    """The class is used to induce faults on bus for dynamic simulation studies. Subclass of the :class:`PyDSS.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

    :param FaultObj: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type FaultObj: class:`PyDSS.dssElement.dssElement`
    :param Settings: A dictionary that defines the settings for the faul controller.
    :type Settings: dict
    :param dssInstance: An :class:`opendssdirect` instance
    :type dssInstance: :class:`opendssdirect` instance
    :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit ojects
    :type ElmObjectList: dict
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`
    :raises: AssertionError  if 'FaultObj' is not a wrapped OpenDSS Fault element

    """
    def __init__(self, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings):
        """Constructor method
        """
        self.__settings = simulationSettings
        super(AutomatedThermalUpgrade_helper).__init__()
        self.__dssinstance = dssInstance
        return

    def run(self, step, stepMax, simulation=None):
        """Induces and removes a fault as the simulation runs as per user defined settings.
        """

        return step
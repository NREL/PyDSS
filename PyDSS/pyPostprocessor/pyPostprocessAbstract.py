
import abc
import os

from PyDSS.exceptions import InvalidParameter
from PyDSS.utils.utils import load_data


class AbstractPostprocess(abc.ABC):
    """An abstract class that serves as template for all pyPlot classes in :mod:`PyDSS.pyPlots.Plots` module.

    :param project: A :class:`PyDSS.pydss_project.PyDssProject` object representing a project
    :type project: PyDssProject
    :param scenario: A :class:`PyDSS.pydss_project.PyDssScenario` object representing a scenario
    :type scenario: PyDssScenario
    :param inputs: user inputs
    :type inputs: dict
    :param dssInstance: A :class:`PyDSS.dssElement.dssElement` object that wraps around an OpenDSS 'Fault' element
    :type dssInstance: dict
    :param dssBuses: Dictionary of all :class:`PyDSS.dssBus.dssBus` objects in PyDSS
    :type dssBuses: dict of :class:`PyDSS.dssBus.dssBus` objects
    :param dssObjects: Dictionary of all :class:`PyDSS.dssElement.dssElement` objects in PyDSS
    :type dssObjects: dict of :class:`PyDSS.dssElement.dssElement` objects
    :param dssObjectsByClass:  Dictionary of all :class:`PyDSS.dssElement.dssElement` objects in PyDSS sorted by class
    :type dssObjectsByClass: dict of :class:`PyDSS.dssElement.dssElement` objects
    :param dssSolver: An instance of one of the classes defined in :mod:`PyDSS.SolveMode`.
    :type dssSolver: :mod:`PyDSS.SolveMode`

    """

    def __init__(self, project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, logger):
        """This is the constructor class.
        """
        self.project = project
        self.scenario = scenario
        if inputs.config_file == "":
            self.config = {}
        else:
            self.config = load_data(inputs.config_file)
        self.config["Outputs"] = project.get_post_process_directory(scenario.name)
        os.makedirs(self.config["Outputs"], exist_ok=True)
        self.Settings = simulationSettings

        self._dssInstance = dssInstance
        self.logger = logger
        self._check_input_fields()

    @abc.abstractmethod
    def run(self, step, stepMax, simulation=None):
        """Method used to run a post processing script.

        Parameters
        ----------
        step : int
            Current step
        stepMax : int
            Last step of the simulation
        simulation : OpenDSS
            PyDSS simulation control class. Provided for access to control algorithms.
            Subclasses should not hold references to this instance after this method exits.

        """

    @abc.abstractmethod
    def _get_required_input_fields(self):
        """Return the required input fields."""

    @abc.abstractmethod
    def finalize(self):
        """Method used to combine post processing results from all steps.
        """
        
    def _check_input_fields(self):
        required_fields = self._get_required_input_fields()
        fields = set(self.config.keys())
        for field in required_fields:
            if field not in fields:
                raise InvalidParameter(f"{self.__class__.__name__} requires input field {field}")

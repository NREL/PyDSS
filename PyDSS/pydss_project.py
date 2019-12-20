"""Contains functionality to configure PyDSS simulations."""

import logging
import os

import PyDSS
from PyDSS.pyDSS import instance
from PyDSS.utils import dump_data, load_data


logger = logging.getLogger(__name__)


DEFAULT_SIMULATION_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS",
    "default_simulation_settings.toml"
)
DEFAULT_CONTROLLER_CONFIG_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS",
    "controllers.toml"
)
DEFAULT_PLOT_SETTINGS_FILE = os.path.join(
    os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS",
    "default_plot_settings.toml"
)

DEFAULT_CONTROLLER_CONFIG = load_data(DEFAULT_CONTROLLER_CONFIG_FILE)
DEFAULT_PYDSS_SIMULATION_CONFIG = load_data(DEFAULT_SIMULATION_SETTINGS_FILE)
DEFAULT_PLOT_CONFIG = load_data(DEFAULT_PLOT_SETTINGS_FILE)
DEFAULT_EXPORT_BY_CLASS = {
    "Circuits": [
        "AllBusMagPu",
        "LineLosses",
        "Losses",
        "TotalPower",
    ],
    "Transformers": [
        "Currents",
        "Losses",
        "NormalAmps",
        "Powers",
        "tap",
    ],
    "Buses": [
        "Distance",
        "puVmagAngle",
    ],
    "Lines": [
        "Currents",
        "Losses",
        "NormalAmps",
        "Powers",
    ],
    "Loads": [
        "Powers",
    ],
    "PVSystems": [
        "Powers",
        "Pmpp",
    ],
}
DEFAULT_EXPORT_BY_ELEMENT = {
    "Storage.storagebus": [
        "pf",
        "%stored",
    ],
    "Load.oh_264928_1_19": [
        "pf",
    ],
}


class PyDssProject:
    """Represents the project options for a PyDSS simulation."""

    _SCENARIOS = "Scenarios"
    _SIMULATION_FILE = "simulation.toml"
    _PROJECT_DIRECTORIES = ("DSSfiles", "Exports", "Logs", "Scenarios")

    def __init__(self, path, name, scenarios, simulation_config):
        self._name = name
        self._scenarios = scenarios
        self._simulation_config = simulation_config
        self._project_dir = os.path.join(path, self._name)
        self._scenarios_dir = os.path.join(self._project_dir, self._SCENARIOS)
        self._dss_dir = os.path.join(self._project_dir, "DSSfiles")

    @property
    def name(self):
        """Return the project name.

        Returns
        -------
        str

        """
        return self._name

    @property
    def scenarios(self):
        """Return the project scenarios.

        Returns
        -------
        list
            list of PyDssScenario

        """
        return self._scenarios

    @property
    def simulation_config(self):
        """Return the simulation configuration

        Returns
        -------
        dict

        """
        return self._simulation_config

    def serialize(self):
        """Create the project on the filesystem."""
        os.makedirs(self._project_dir, exist_ok=True)
        for name in self._PROJECT_DIRECTORIES:
            os.makedirs(os.path.join(self._project_dir, name), exist_ok=True)

        dump_data(
            self._simulation_config,
            os.path.join(self._project_dir, self._SIMULATION_FILE),
        )

        for scenario in self._scenarios:
            scenario.serialize(
                os.path.join(self._scenarios_dir, scenario.name)
            )

        logger.info("Setup folders at %s", self._project_dir)

    @classmethod
    def create_project(cls, path, name, scenarios, simulation_config=None):
        """Create a new PyDssProject on the filesystem.

        Parameters
        ----------
        path : str
            path in which to create directories
        name : str
            project name
        scenarios : list
            list of PyDssScenario objects
        simulation_config : str
            simulation config file; if None, use default

        """
        if simulation_config is None:
            simulation_config = DEFAULT_SIMULATION_SETTINGS_FILE
        simulation_config = load_data(simulation_config)
        simulation_config["Project Path"] = path
        simulation_config["Active Project"] = name
        project = cls(path, name, scenarios, simulation_config)
        project.serialize()
        logger.info("Created project=%s with scenarios=%s at %s", name,
                    scenarios, path)
        return project

    def run(self):
        """Run all scenarios in the project."""
        inst = instance()
        for scenario in self._scenarios:
            self._simulation_config["Active Scenario"] = scenario.name
            inst.run(self._simulation_config, scenario)

    @classmethod
    def load_project(cls, path):
        """Load a PyDssProject from directory.

        Parameters
        ----------
        path : str
            full path to existing project

        """
        name = os.path.basename(path)
        scenarios_dir = os.path.join(path, PyDssProject._SCENARIOS)
        scenarios = [PyDssScenario.deserialize(os.path.join(scenarios_dir, x))
                     for x in os.listdir(scenarios_dir)]
        simulation_config = load_data(
            os.path.join(path, PyDssProject._SIMULATION_FILE)
        )
        return PyDssProject(path, name, scenarios, simulation_config)

    @classmethod
    def run_project(cls, path):
        """Load a PyDssProject from directory and run all scenarios.

        Parameters
        ----------
        path : str
            full path to existing project

        """
        project = cls.load_project(path)
        return project.run()


class PyDssScenario:
    """Represents a PyDSS Scenario."""

    _CONTROLLERS_FILENAME = "controllers.toml"
    _EXPORTS_FILENAME = "exports.toml"
    _PLOTS_FILENAME = "plots.toml"
    _SCENARIO_DIRECTORIES = ("ExportLists", "pyControllerList", "pyPlotList")

    def __init__(self, name, controllers=None, exports=None, plots=None):
        self.name = name
        if exports is None:
            self.exports = DEFAULT_EXPORT_BY_CLASS
        elif isinstance(exports, str):
            self.exports = load_data(exports)
        else:
            self.exports = exports

        if controllers is None:
            self.controllers = {"default": DEFAULT_CONTROLLER_CONFIG["default"]}
        elif isinstance(controllers, str):
            self.controllers = load_data(controllers)
        else:
            self.controllers = controllers

        if plots is None:
            self.plots = DEFAULT_PLOT_CONFIG
        elif isinstance(plots, str):
            self.plots = load_data(plots)
        else:
            self.plots = plots

    @classmethod
    def deserialize(cls, path):
        """Deserialize a PyDssScenario from a path.

        Parameters
        ----------
        path : str
            full path to scenario

        Returns
        -------
        PyDssScenario

        """
        name = os.path.basename(path)
        controllers = load_config(os.path.join(path, "pyControllerList"))
        exports = load_config(os.path.join(path, "ExportLists"))
        plots = load_config(os.path.join(path, "pyPlotList"))
        return cls(name, controllers=controllers, exports=exports, plots=plots)

    def serialize(self, path):
        """Serialize a PyDssScenario to a directory.

        Parameters
        ----------
        path : str
            full path to scenario

        """
        os.makedirs(path, exist_ok=True)
        for name in self._SCENARIO_DIRECTORIES:
            os.makedirs(os.path.join(path, name), exist_ok=True)

        dump_data(
            self.controllers,
            os.path.join(path, "pyControllerList", self._CONTROLLERS_FILENAME),
        )
        dump_data(
            self.exports,
            os.path.join(path, "ExportLists", self._EXPORTS_FILENAME),
        )
        dump_data(
            self.plots,
            os.path.join(path, "pyPlotList", self._PLOTS_FILENAME),
        )


def load_config(path):
    """Return a configuration from files.

    Parameters
    ----------
    path : str

    Returns
    -------
    dict

    """
    files = [os.path.join(path, x) for x in os.listdir(path) \
             if os.path.splitext(x)[1] == ".toml"]
    assert len(files) == 1, "only 1 .toml file is currently supported"
    return load_data(files[0])

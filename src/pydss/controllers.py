
from typing import Optional, Annotated
from collections import defaultdict
from  loguru import logger
import json
import abc

from pydantic import BaseModel, Field
from pydantic import ConfigDict
import opendssdirect as dss

from pydss.exceptions import InvalidConfiguration, OpenDssConvergenceError
from pydss.pyControllers.Controllers.PvController import PvController
from pydss.utils.timing_utils import TimerStatsCollector, Timer
from pydss.utils.dss_utils import list_element_names_by_class
from pydss.dssInstance import OpenDSS, CONTROLLER_PRIORITIES
from pydss.SolveMode import get_solver_from_simulation_type
from pydss.simulation_input_models import ProjectModel
from pydss.modes.solver_base import solver_base


class ControllerBaseModel(BaseModel, abc.ABC):
    model_config = ConfigDict(title="ControllerBaseModel", str_strip_whitespace=True, validate_assignment=True, validate_default=True, extra="forbid", use_enum_values=False, populate_by_name=True)

    @staticmethod
    @abc.abstractmethod
    def get_controller_class():
        """Return the pydss controller class for the model."""

    @staticmethod
    @abc.abstractmethod
    def get_element_class():
        """Return the OpenDSS element class for the controller."""


class PvControllerModel(ControllerBaseModel):
    control1: Annotated[
        str,
        Field(
            title="Control1",
            description="Algorithm to run in the first control loop",
            alias="Control1",
        )]
    control2: Optional[str] = Field(
        title="Control1",
        description="Algorithm to run in the second control loop",
        alias="Control2",
    )
    control3: Optional[str] = Field(
        title="Control3",
        description="Algorithm to run in the third control loop",
        alias="Control3",
    )
    pf: int = Field(
        title="pf",
        description="Power factor for the PV system",
    )
    pf_min: Annotated[
        float,
        Field(
            title="pfMin",
            description="Minimum allowable power factor for the PV system. Applied only if enable_pf_limit is set.",
            alias="pfMin",
        )]
    pf_max: Annotated[
        float,
        Field(
            title="pfMax",
            description="Maximum allowable power factor for the PV system. Applied only if enable_pf_limit is set.",
            alias="pfMax",
        )]
    p_min: Annotated[
        float,
        Field(
            title="Pmin",
            description="TODO",
            alias="Pmin",
        )]
    p_max:Annotated[
        float,
        Field(
            title="Pmax",
            description="TODO",
            alias="Pmax",
        )]
    u_min: Annotated[
        float,
        Field(
            title="uMin",
            description="Per unit voltage value at which inverter produces maximum vars. (volt / var algorithm).",
            alias="uMin",
        )]
    u_db_min: Annotated[
        float,
        Field(
            title="uDbMin",
            description="Lower bound for the voltage deadband [per unit]. Inverter will not produce or consume vars within these bands (volt / var algorithm).",
            alias="uDbMin",
        )]
    u_db_max: Annotated[
        float,
        Field(
            title="uDbMax",
            description="Upper bound for the voltage deadband [per unit]. Inverter will not produce or consume vars within these bands (volt / var algorithm).",
            alias="uDbMax",
        )]
    u_max: Annotated[
        float,
        Field(
            title="uMax",
            description="Per unit voltage value at which inverter consumes maximum vars (volt / var algorithm).",
            alias="uMax",
        )]
    q_lim_pu: Annotated[
        float,
        Field(
            title="QlimPU",
            description="Inverter reactive power limit [per unit] for the volt / var algorithm.",
            alias="QlimPU",
        )]
    pf_lim: Annotated[
        float,
        Field(
            title="PFlim",
            description="Inverter power factor limit. Applied only if enable_pf_limit is set.",
            alias="PFlim",
        )]
    enable_pf_limit: Annotated[
        bool,
        Field(
            title="EnablePFLimit",
            description="Flag to enable / disable power factor limits on the inverter",
            alias="Enable PF limit",
        )]
    u_min_c: Annotated[
        float,
        Field(
            title="uMinC",
            description="Lower voltage bound [per unit] for the volt / watt algorithm",
            alias="uMinC",
        )]
    u_max_c: Annotated[
        float,
        Field(
            title="uMaxC",
            description="Upper voltage bound [per unit] for the volt / watt algorithm",
            alias="uMaxC",
        )]
    p_min_vw: Annotated[
        float,
        Field(
            title="PminVW",
            description="Lower bound for the inveter active power output for the volt / watt algorithm",
            alias="PminVW",
        )]
    vw_type: Annotated[
        str,
        Field(
            title="VWtype",
            description="volt / watt algorithm to be implemented on rated or available power",
            alias="VWtype",
        )]
    percent_p_cutin: Annotated[
        float,
        Field(
            title="PCutin",
            description="Percentage cut-in power -- Percentage of kVA rating of inverter. When the inverter is OFF, the power from the array must be greater than this for the inverter to turn on.",
            alias="%PCutin",
        )]
    percent_p_cutout: Annotated[
        float,
        Field(
            title="%PCutout",
            description="Percentage cut-out power -- Percentage of kVA rating of inverter. When the inverter is ON, the inverter turns OFF when the power from the array drops below this value.",
            alias="%PCutout",
        )]
    efficiency: Annotated[
        float,
        Field(
            title="Efficiency",
            description="Efficieny of the inverter system",
            alias="Efficiency",
        )]
    priority: Annotated[
        str,
        Field(
            title="Priority",
            description="Set export priority for active power or reactive power",
            alias="Priority",
        )]
    damp_coef: Annotated[
        float,
        Field(
            title="DampCoef",
            description="Damping cooefficient for the convergence algorithm",
            alias="DampCoef",
        )]

    @staticmethod
    def get_controller_class():
        return PvController

    @staticmethod
    def get_element_class():
        return dss.PVsystems


def make_default_volt_var_controller():
    return PvControllerModel(
        Control1="VVar",
        Control2="None",
        Control3="None",
        pf=1,
        pfMin=0.8,
        pfMax=1,
        Pmin=0,
        Pmax=1,
        uMin=0.9399999999999999,
        uDbMin=0.97,
        uDbMax=1.03,
        uMax=1.06,
        QlimPU=0.44,
        PFlim=0.9,
        enable_pf_limit=False,
        uMinC=1.06,
        uMaxC=1.1,
        PminVW=10,
        VWtype="Rated Power",
        percent_p_cutin=10,
        percent_p_cutout=10,
        Efficiency=100,
        Priority="Var",
        DampCoef=0.8,
    )


class CircuitElementController:
    """Contains a controller model and elements to control."""

    def __init__(self, controller_model: ControllerBaseModel, element_names=None):
        """
        Parameters
        ----------
        controller_model: ControllerBaseModel
        element_names: list | None
            List of element names (str). If None, use all elements for the given class.

        """
        self._controller_model = controller_model
        if element_names is None:
            self._element_names = list_element_names_by_class(self.get_element_class())
        else:
            self._element_names = element_names

    @property
    def controller_model(self):
        return self._controller_model

    @property
    def element_names(self):
        return self._element_names

    def get_controller_class(self):
        return type(self._controller_model).get_controller_class()

    def get_element_class(self):
        return type(self._controller_model).get_element_class()


class ControllerManager:
    """Provides ability to run control algorithms on circuit elements."""

    def __init__(self, controllers: dict, solver: solver_base, max_control_iterations: int, error_tolerance: float):
        self._controllers = controllers
        self._max_control_iterations = max_control_iterations
        self._error_tolerance = error_tolerance
        self._solver = solver
        self._stats = TimerStatsCollector()

    @classmethod
    def create(cls, controllers: list, settings: ProjectModel):
        """Create controllers. The circuit must be loaded in OpenDSS."""
        solver = get_solver_from_simulation_type(settings)
        buses = OpenDSS.CreateBusObjects()
        elements, elements_by_class = OpenDSS.CreateDssObjects(buses)
        controllers_by_class = defaultdict(dict)
        for circuit_element_controller in controllers:
            controller_class = circuit_element_controller.get_controller_class()
            element_class = circuit_element_controller.get_element_class()
            for name in circuit_element_controller.element_names:
                element = elements.get(name)
                if element is None:
                    raise InvalidConfiguration(f"{name} is not in the circuit")
                controller = controller_class(
                    element,
                    circuit_element_controller.controller_model.dict(by_alias=True),
                    dss,
                    elements,
                    solver,
                )
                controllers_by_class[element_class]["Controller." + name] = controller

        return cls(
            controllers_by_class,
            solver,
            settings.max_control_iterations,
            settings.error_tolerance,
        )

    def run_controls(self):
        """Run all controls.

        Returns
        -------
        bool
            True if all controllers converged, otherwise False.

        """
        has_converged = True
        with Timer(self._stats, "RunControls"):
            for priority in range(CONTROLLER_PRIORITIES):
                priority_has_converged = False
                for i in range(self._max_control_iterations):
                    if self._update_controllers(priority, i):
                        priority_has_converged = True
                        break
                    if not self._solver.reSolve():
                        raise OpenDssConvergenceError(f"OpenDSS did not converge after update")
                if not priority_has_converged:
                    has_converged = False

        return has_converged

    def _update_controllers(self, priority, iteration):
        maxError = 0

        for element_class, elements in self._controllers.items():
            elm = element_class.First()
            while elm:
                element_name = dss.CktElement.Name()
                controller_name = 'Controller.' + element_name
                if controller_name in elements:
                    controller = elements[controller_name]
                    error = controller.Update(priority, iteration, False)
                    maxError = error if error > maxError else maxError
                    if iteration == self._max_control_iterations - 1:
                        if error > self._error_tolerance:
                            errorTag = {
                                "Report": "Convergence",
                                #"Scenario": self._settings.active_scenario,
                                "Time": self._solver.GetTotalSeconds(),
                                "DateTime": str(self._solver.GetDateTime()),
                                "Controller": controller.Name(),
                                "Controlled element": controller.ControlledElement(),
                                "Error": error,
                                "Control algorithm": controller.debugInfo()[priority],
                            }
                            json_object = json.dumps(errorTag)
                            # TODO: Make reports logger
                            logger.warning(json_object)
                elm = element_class.Next()
        return maxError < self._error_tolerance

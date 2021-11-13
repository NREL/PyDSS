"""Example file to demonstrate how to use PyDSS controllers"""

import opendssdirect as dss

from PyDSS.controllers import (
    CircuitElementController,
    ControllerManager,
    PvControllerModel,
)
from PyDSS.simulation_input_models import ProjectModel


def main():
    settings = ProjectModel(
        max_control_iterations=50,
        error_tolerance=0.0001,
    )
    dss.run_command("compile opendss_models/Master.dss")
    dss.Solution.Mode(0)
    dss.utils.run_command("Set ControlMode={}".format(settings.control_mode.value))
    dss.Solution.MaxControlIterations(settings.max_control_iterations)

    volt_var_model = PvControllerModel(
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
    controller = CircuitElementController(volt_var_model)  # Use all elements.
    manager = ControllerManager.create([controller], settings)

    done = False
    while not done:
        has_converged = manager.run_controls()
        if has_converged:
            print("Reached convergence")
            done = True
        else:
            # TODO: just an example. Real code would have other logic.
            raise Exception("Failed to converge")


if __name__ == "__main__":
    main()

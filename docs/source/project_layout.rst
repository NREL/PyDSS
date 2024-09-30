.. _pydss_project_layout:

********************
Pydss Project Layout
********************
A pydss project is made up of one or more scenarios that run simulations on a shared OpenDSS
model. The purpose of scenarios is to allow users to customize inputs, outputs, or controls.
Here are some examples to define multiple scenarios:

- Run different control algorithms.
- Run snapshot simulations at different time points.
- Generate custom plots.
- Run custom post-process scripts after each call to ``Solve``.

Simulation Settings
===================
The main configuration file for the simulation is stored at ``<project-name>/simulation.toml``.
Refer to :ref:`SimulationSettingsModel` for more information. The following model defines all options valid for the simulation.toml file

.. .. autopydantic_settings:: pydss.simulation_input_models.SimulationSettingsModel

Scenarios
=========
Each scenario provides customizable config files in ``<project-name>/Scenarios/<scenario-name>``.
Refer to these subdirectories:

- pyControllerList
- ExportLists

.. TODO: write detailed sections for existing controllers and how to develop custom controllers

Exports
=======
If ``export_results`` is enabled then exported data for each scenario will be located in output
directories at ``<project-name>/Exports/<scenario-name>/``.

Reports
=======
If any reports are enabled then generated report files will be located in the output
directory ``<project-name>/Reports/``.

Example layout
==============
Here is an example project that uses different controllers for each scenario.

::

    tree examples/custom_contols
    examples/custom_contols
    ├── DSSfiles
    │   ├── HECO19021_Profile9998.DSV
    │   ├── HECO19021_Profile9998.dbl
    │   ├── HECO19021_VLN_Node.Txt
    │   ├── Loadshapes_Sep8to15.dss
    │   ├── MPX000460267.csv
    │   ├── MPX000472455.csv
    │   ├── MPX000594341.csv
    │   ├── MPX000635970.csv
    │   ├── MPX000637601.csv
    │   ├── Master_Spohn_existing_VV.dss
    │   ├── PVGenerators_existing_VV.dss
    │   ├── SecLines.dss
    │   ├── SecLoads_Timeseries_realloc.dss
    │   ├── Vsource_profile.csv
    │   ├── buscoords.dss
    │   └── testcodes.dss
    ├── Exports
    ├── ProfileManager.toml
    ├── Profiles
    │   ├── mapping.toml
    │   └── profiles.hdf5
    ├── Scenarios
    │   ├── base_case
    │   │   ├── ExportLists
    │   │   │   └── ExportMode-byClass.toml
    │   │   ├── pyControllerList
    │   │   └── pyPlotList
    │   ├── multiple_controls
    │   │   ├── ExportLists
    │   │   │   └── ExportMode-byClass.toml
    │   │   ├── PostProcess
    │   │   ├── pyControllerList
    │   │   │   ├── PvController.toml
    │   │   │   └── StorageController.toml
    │   │   └── pyPlotList
    │   ├── self_consumption
    │   │   ├── ExportLists
    │   │   │   └── ExportMode-byClass.toml
    │   │   ├── PostProcess
    │   │   ├── pyControllerList
    │   │   │   └── StorageController.toml
    │   │   └── pyPlotList
    ├── simulation.toml

.. _quick_start_label:

*****************
Quick Start Guide
*****************

This page provides a short example to get pydss up and running. If you have not already installed
pydss, please follow the instructions at :ref:`installation_label`.

The basic steps are to create an empty project, copy your OpenDSS model files into that project,
customize the simuation settings, and then run the simulation.

Create an empty project
=======================
Pydss requires a specific directory structure with configuration files that specify how to run a
simulation. Run this command to create an empty project.

.. code-block:: bash

    $ pydss create-project --project=my-project --scenarios="scenario1,scenario2" --path=./pydss-projects

Customize the simulation settings
=================================
The file ``./pydss-projects/my-project/simulation.toml`` is the main configuration file for the
project. Refer to :ref:`simulation_settings_label` for help.

Each scenario has its own config files for additional customization, such as for custom controls,
data export, and plotting. Refer to the ``.toml`` files in subdirectories in
``./pydss-projects/my-project/Scenarios/<scenario-name>``.

Refer to :ref:`pydss_project_layout` for more information about the project layout.

OpenDSS Models
==============

1. Copy your OpenDSS model files into ``./pydss-projects/my-project/DSSfiles/``.
2. Set the field ``dss_file`` in ``simulation.toml`` to the OpenDSS entry point filename
   (e.g., Master.dss).

Run the simulation
==================

.. code-block:: bash

   $ pydss run ./pydss-projects/my-project/

Results
=======
If you enabled data exports or reports, the files will be in
``./pydss-projects/my-project/Exports/<scenario-name>/`` or
``./pydss-projects/my-project/Reports``.

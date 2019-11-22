Improved project management
===========================

When working on numerous project each with multiple scenarios, management of project with OpenDSS becomes challenging. PyDSS aims to resolve this issue by providing a project management schema shown below. The schema allows user to define projects and multiple scenarios for each project. The schema also manages exported results ans logs that becomes very handy when working with a large number of feeders.

The schema is PyDSS follows is as follows:

.. code-block:: python

	~\PyDSS-Projects (There should be no spaces in the complete base path)
            |__ \IEEE13node
            |      |__ \DSSfiles (Should contain OpenDSS files)
            |      |__ \PyDSS Scenarios (All scenarios should be defined within this folder)
            |      |       |__ \Self_consumption (A PyDSS scenario will be defined within this directory)
            |      |       |       |__ \ExportLists.json (Define export list for the project)
            |      |       |       |__ \pyControllerList.json (Define a set of custom controls)
            |      |       |       |__ \pyPlotList.json (Define a set of dynamic plots)
            |      |       |       |__ \Scenario_settings.toml (PyDSS simulation settings)			
            |      |       |__ \HELICS 
            |      |       |__ \<Scenario name> 
            |      |       |__ \Batch_settings.toml (The batch toml file is required to run batch simulations)			
            |      |               :			
            |      |__ \Exports (All simulation results will be exported to this folder)
            |      |__ \Logs (PyDSS logs will be exported to this folder)
            |__ \EPRIJ1feeder
            |__ \<Project name>
                   :

The use of TOML files ensure reproducability of results as it contains all the simulaation settings used for generating simulation results. This ensures high quality easily reproducable results.

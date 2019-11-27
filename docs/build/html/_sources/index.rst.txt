.. PyDSS documentation master file, created by
   sphinx-quickstart on Mon Oct 21 12:01:13 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. figure::  _static/Logo.png
   :align:   center

About PyDSS
===========
PyDSS is a high-level Python package that is a wrapper for OpenDSS and aims to expand upon its organizational, analytical, and visualization capabilities. Further, it simplifies co-simulation framework integration and allows the user to develop custom control algorithms and embed them into the simulation environment. PyDSS makes use of opendssdirect.py (https://pypi.org/project/OpenDSSDirect.py/) to provide a high-level Python interface for OpenDSS. PyDSS also provides extension modules to facilitate Monte Carlo studies in distribution system domain and automated post processing of results. Flexible architecture makes PyDSS customizable and easily extendible. 

Installation
============

PyDSS can be installed by typing the following command on the command prompt:

.. code-block:: python

	pip install -i https://test.pypi.org/simple/ PyDSS==0.0.1
	
Alternately, if you choose to clone the git repo from https://github.com/nrel/pydss , use the followiing commands to build the module and install it.

.. code-block:: python

	python setup.py -build
	python setup.py -install

Running PyDSS
=============

Running PyDSS requires a valid OpenDSS model to run. Additionally, it requires a development of a project structure detailed  in the following subsections.

Settings up a PyDSS project
~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyDSS requires a specific directory format to define projects detailed below.
 
.. code-block:: python

	~\PyDSS-Projects (There should be no spaces in the complete base path)
            |__ \IEEE13node
            |      |__ \DSSfiles (Should contain OpenDSS files)
            |      |__ \PyDSS Scenarios (All scenarios should be defined within this folder)
            |      |       |__ \Self_consumption (A PyDSS scenario will be defined within this directory)
            |      |       |       |__ \ExportLists.json (Define export list for the project)
            |      |       |       |__ \pyControllerList.json (Define a set of custom controls)
            |      |       |       |__ \pyPlotList.json (Define a set of dynamic plots)
            |      |       |       |__ \*Scenario_settings*.toml (PyDSS simulation settings)			
            |      |       |__ \HELICS 
            |      |       |__ \<Scenario name> 
            |      |       |__ \*Vis_settings*.toml (The batch toml file is required to run batch simulations)			
            |      |               :			
            |      |__ \Exports (All simulation results will be exported to this folder)
            |      |__ \Logs (PyDSS logs will be exported to this folder)
            |__ \EPRIJ1feeder
            |__ \<Project name>
                   :
			   
Running PyDSS is simple. The following code snippet shows how to run a defined simulation scenario.


.. code-block:: python

	import click
	import sys
	import os

	@click.command()
	@click.option('--pydss_path',
				  default=r'C:\\Users\\alatif\\Desktop\\PyDSS')
	@click.option('--sim_path',
				  default=r'~PyDSS\\examples\\Custom_controls_example\\PyDSS Scenarios')
	@click.option('--sim_file',
				  default=r'multiple_controllers.toml') #The TOML file contains simulation settings for the particular scenario
	@click.option('--vis_file',
				  default=r'automated_comparison.toml') #The TOML file contains visualization settings 
	def run_pyDSS(pydss_path, sim_path, sim_file, vis_file):
		# Should not be required if installed using pip command. Only required when working with a cloned copy.
		sys.path.append(pydss_path) 
		sys.path.append(os.path.join(pydss_path, 'PyDSS'))
		from pyDSS import instance as dssInstance
		# Create an instance of PyDSS
		a = dssInstance() 
		#Run the simulation 
		a.run(sim_file, vis_file) 

	run_pyDSS()

- sim_file [str or list[str]] -  Path to simulation settings toml file. Can be a list of paths. If a list is provided, simulations will be run sequentially.
- vis_file [str] - Path to visualization settings toml file. Is only required when generating comparativce plots


Skeleton for a new project can be created using following lines of code.  

.. code-block:: python

	from PyDSS import PyDSS
	sucess = PyDSS.create('<Proects path>', '<Project name>', '<Scenario name>')
	
After executing the following lines of code, user will be prompted to answer a few questions, that will enable PyDSS to automate creation of a skeleton of a new project. 

Validity of the PyDSS project can be tested using the following command.  	

.. code-block:: python

	from PyDSS import PyDSS
	sucess = PyDSS.test('<Proects path>', '<Project name>')

Within the installation folder, several examples have been provided.
	
Default values for the simulation settings and visualization settigs can be found here.
	
.. toctree::
   :maxdepth: 2
   
   Sample TOML files  
   
Additional Documentation
========================

.. toctree::
   :maxdepth: 1

   Simulation modes
   Project management
   Result management
   Dynamic visualization capabilities
   Extended controls library
   External interfaces for cosimulation
   Automated comparison of scenarios
   
   
License
=======

BSD 3-Clause License

Copyright (c) 2018, Alliance for Sustainable Energy LLC, All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

- Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Contact
=======
Questions? Please send an email to aadil.latif@nrel.gov or aadil.latif@gmail.com

   

Indices and tables
^^^^^^^^^^^^^^^^^^

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. PyDSS documentation master file, created by
   sphinx-quickstart on Mon Oct 21 12:01:13 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. figure::  _static/Logo.png
   :align:   center

#####
PyDSS
#####

***********
About PyDSS
***********
PyDSS is a Python wrapper for OpenDSS that aims to expand upon its
organizational, analytical, and visualization capabilities with these features:

- Allows the user to develop custom control algorithms for specific circuit elements and run them
  at each simulation time step.
- Provides co-simulation integration with HELICS.
- Provides extension modules to facilitate Monte Carlo studies in distribution system domain and
  automated post-processing of results.
- Automates collection and analysis of circuit element results at each simulation time step.
- Flexible architecture allows users to develop extensions.

PyDSS uses opendssdirect.py (https://pypi.org/project/OpenDSSDirect.py/) to communicate with
OpenDSS.

.. _installation_label:

************
Installation
************

Recommendation: Install PyDSS in an Anaconda virtual environment. Specific dependent
packages like shapely will only install successfully on Windows with conda.

Here is an example conda command:

.. code-block:: bash

    $ conda create -n pydss python=3.9

Install shapely with conda. pip, particularly on Windows, often fails to install its dependent
libraries.

.. code-block:: bash

    $ conda install shapely

Install the latest supported PyDSS version with this command:

.. code-block:: bash

    $ pip install dsspy
	
Alternatively, to get the lastest code from the master branch:

.. code-block:: bash

    $ git clone https://github.com/NREL/PyDSS
    $ pip install -e PyDSS

Confirm the installation with this command. It should print the available commands::

    $ pydss --help


*************
Running PyDSS
*************
Refer to the :ref:`quick_start_label` for basic instructions on how to configure PyDSS to run a
simulation with an existing OpenDSS model.

Refer to :ref:`tutorial_label` for in-depth instructions on how to customize a PyDSS project.

Refer to :ref:`examples_label` for example simulations covering various use cases.

   
************************
Additional Documentation
************************

.. toctree::
   :maxdepth: 1

   quickstart
   tutorial
   project_layout
   simulation_settings
   examples
   Result management
   reports
   hdf-data-format
   controllers
   PyDSS
   
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
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

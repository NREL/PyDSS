.. pydss documentation master file, created by
   sphinx-quickstart on Mon Oct 21 12:01:13 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#####
Pydss
#####

***********
About Pydss
***********

Pydss is a Python wrapper for OpenDSS that aims to expand upon its
organizational, analytical, and visualization capabilities with these features:

- Allows the user to develop custom control algorithms for specific circuit elements and run them
  at each simulation time step.
- Provides co-simulation integration with HELICS.
- Provides extension modules to facilitate Monte Carlo studies in distribution system domain and
  automated post-processing of results.
- Automates collection and analysis of circuit element results at each simulation time step.
- Flexible architecture allows users to develop extensions.

Pydss uses opendssdirect.py (https://pypi.org/project/OpenDSSDirect.py/) to communicate with
OpenDSS.

.. _installation_label:

************
Installation
************

Recommendation: Install pydss in an Anaconda virtual environment. Specific dependent
packages like shapely will only install successfully on Windows with conda.

Here is an example conda command:

.. code-block:: bash

    $ conda create -n pydss python=3.9


Install the latest supported pydss version with this command:

.. code-block:: bash

    $ pip install NREL-pydss
	
Alternatively, to get the lastest code from the master branch:

.. code-block:: bash

    $ git clone https://github.com/NREL/PyDSS
    $ pip install -e PyDSS

Confirm the installation with this command. It should print the available commands::

    $ pydss --help


*************
Running PyDSS
*************
Refer to the :ref:`quick_start_label` for basic instructions on how to configure pydss to run a
simulation with an existing OpenDSS model.

Refer to :ref:`tutorial_label` for in-depth instructions on how to customize a pydss project.


************************
Additional Documentation
************************

.. toctree::
   :maxdepth: 1

   quickstart
   tutorial
   interfaces
   project_layout
   reports
   hdf-data-format
   co-simulation_support
   controllers_overview
   
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

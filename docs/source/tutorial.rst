Tutorial
########
This page describes how to run simulations with PyDSS.

Installation
************
There are two ways to install PyDSS.

1. Install via pip.

::

    pip install -i https://test.pypi.org/simple/ PyDSS==0.0.1

2. Clone the repository.

::

   git clone https://github.com/NREL/PyDSS
   cd PyDSS
   pip install -e .


Confirm the installation with this command. It should print the available
commands::

    pydss --help

Create a new project
********************
PyDSS requires a specific directory layout.  Use this command to create an
empty project. ::

    pydss create-project --project=my_project \
        --scenarios="scenario1,scenario2" \
        --path=~/pydss-projects

Refer to ``pydss create-project --help`` to see additional options.

Next, configure the project.

- Copy OpenDSS files to <project-name>/DSSfiles
- Customize the simulation settings in <project-name>/simulation.toml.
  In particular, set the value for "DSS File" to the master file in the
  DSSfiles directory.
- Customize the PyDSS controllers in
  <project-name>/Scenarios/<scenario-name>/pyControllerList.
  There needs to be one controller section for each PVSystem defined in the
  OpenDSS configuration. The name of each section must be the PVSystem
  identifier (replace "PVSystem.pv1234" with your names).
- Customize the the plots to be generated in
  <project-name>/Scenarios/<scenario-name>/pyPlotList
- Customize data to be exported for each scenario in
  <project-name>/Scenarios/<scenario-name>/ExportLists

Exporting Data
==============
The default behavior of PyDSS is to export raw, unstructured data received from
opendssdirect into CSV files. It is left to the user to interpret this data.

There is a new method of exporting data under development that adds structure
for easier analysis. It currently supports a limited set of element properties.
To enable this behavior set the following in ``simulation.toml``::

    "Result Container" = "ResultData"

Data Format
-----------
These configuration customizations exist for data exported using the new
"ResultData" container:

- "Export Format":  Set to "csv" or "h5"
- "Export Compression":  Set to true or false.
- "Export Elements":  Set to true to export static element parameters.
- "Export Data Tables":  Set to true to export data tables for each element property.
- "Export Data In Memory":  Set to true to keep exported data in memory.
  Otherwise, it is flushed to disk periodically.
  Note that this duplicates data. Enable this to preserve a human-readable
  dataset that does not require PyDSS to interpret.
- "Export Event Log":  Set to true to export the OpenDSS event log.


Run a project
*************
Run this command to run all scenarios in the project.  ::

    pydss run <path-to-project>


Analyze results
***************
If the default export behavior is used then the raw output is written to CSV
files in <project-path>/<project-name>/Export/<scenario-name>. These can be
converted to pandas DataFrames. It is up to the user to interpret what each
column represents.  This can very by element.

If the "ResultData" export method is configured then data can be loaded as
shown by this example code::

Load element classes and properties
===================================

.. code-block:: python

    from PyDSS.pydss_results import PyDssResults

    path = "."
    results = PyDssResults(path)
    scenario = results.scenarios[0]
    # Show the element classes and properties for which data was collected.
    for elem_class in scenario.list_element_classes():
        for prop in scenario.list_element_properties(elem_class):
            for name in scenario.list_element_names(elem_class, prop):
                print(elem_class, prop, name)

Read a dataframe for one element
================================

::

    df = scenario.get_dataframe("Lines", "Currents", "Line.pvl_112")
    df.head()

                                                  Line.pvl_112__A1 [Amps]                        Line.pvl_112__A2 [Amps]
    timestamp
    2017-01-01 00:15:00  (3.5710399970412254e-08+1.3782673590867489e-05j)  (-3.637978807091713e-12+1.1368683772161603e-13j)
    2017-01-01 00:30:00  (3.3905962482094765e-08+1.3793145967611053e-05j)                           1.1368683772161603e-13j
    2017-01-01 00:45:00   (3.381501301191747e-08+1.3786106705993006e-05j)                       (-3.637978807091713e-12+0j)
    2017-01-01 01:00:00  (3.4120603231713176e-08+1.3804576042275585e-05j)   (3.637978807091713e-12+1.1368683772161603e-13j)
    2017-01-01 01:15:00   (3.356035449542105e-08+1.3810414088766265e-05j)  (-3.637978807091713e-12+1.1368683772161603e-13j)

Read a dataframe for one element with a specific option
=======================================================
Some element properties contain multiple values.  For example, the OpenDSS
CktElement objects report ``Currents`` into each phase/terminal.
Here is how you can get the data for a single phase/terminal::

    df = scenario.get_dataframe("Lines", "Currents", "Line.pvl_112", phase_terminal="A1")
    df.head()

                                                   Line.pvl_112__Currents__A1 [Amps]
    timestamp
    2017-01-01 00:15:00  (3.5710399970412254e-08+1.3782673590867489e-05j)
    2017-01-01 00:30:00  (3.3905962482094765e-08+1.3793145967611053e-05j)
    2017-01-01 00:45:00   (3.381501301191747e-08+1.3786106705993006e-05j)
    2017-01-01 01:00:00  (3.4120603231713176e-08+1.3804576042275585e-05j)
    2017-01-01 01:15:00   (3.356035449542105e-08+1.3810414088766265e-05j)

    df = scenario.get_dataframe("Lines", "CurrentsMagAng", "Line.pvl_112", phase_terminal="A1", mag_ang="mag")
    df.head()

                             Line.sw0__A1__mag [Amps]
    timestamp
    2017-01-01 00:15:00                  6.469528
    2017-01-01 00:30:00                  6.474451
    2017-01-01 00:45:00                  6.461993
    2017-01-01 01:00:00                  6.384335
    2017-01-01 01:15:00                  6.347553

Read a dataframe for one element with an option matching a regular expression
=============================================================================

::

    import re
    # Get data for all phases but only terminal 1.
    regex = re.compile(r"[ABCN]1")
    df = scenario.get_dataframe("Lines", "Currents", "Line.pvl_112", phase_terminal=regex)
    df.head()

                                                   Line.pvl_112__Currents__A1 [Amps]
    timestamp
    2017-01-01 00:15:00  (3.5710399970412254e-08+1.3782673590867489e-05j)
    2017-01-01 00:30:00  (3.3905962482094765e-08+1.3793145967611053e-05j)
    2017-01-01 00:45:00   (3.381501301191747e-08+1.3786106705993006e-05j)
    2017-01-01 01:00:00  (3.4120603231713176e-08+1.3804576042275585e-05j)
    2017-01-01 01:15:00   (3.356035449542105e-08+1.3810414088766265e-05j)

Find out all options available for a property
=============================================

::

    scenario.list_element_property_options("Lines", "Currents")
    ["phase_terminal"]

    scenario.list_element_property_options("Lines", "CurrentsMagAng")
    ['phase_terminal', 'mag_ang']

    scenario.list_element_property_options("Lines", "NormalAmps")
    []

Find out what option values are present for a property
======================================================

::

    df = scenario.get_option_values("Lines", "Currents", "Line.pvl_112")
    ["A1", "A2"]

Read a dataframe for all elements
=================================
You may want to get data for all elements at once.

.. code-block:: python

    df = scenario.get_full_dataframe("Lines", "Currents")


Performance Considerations
**************************
If your dataset is small enough to fit in your system's memory then you can
load it all into memory by passing ``in_memory=True`` to ``PyDssResults``.

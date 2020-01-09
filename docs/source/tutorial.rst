Tutorial
########
This page describes how to run simulations with PyDSS.

Installation
************

1. Install via pip. ::

    pip install -i https://test.pypi.org/simple/ PyDSS==0.0.1

2. Clone the repository. ::

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
- Customize the simulation settings in <project-name>/simulation.toml
- Customize data to be exported for each scenario in
  <project-name>/Scenarios/<scenario-name>/ExportLists
- Customize the PyDSS controllers in
  <project-name>/Scenarios/<scenario-name>/pyControllerList
- Customize the the plots to be generated in
  <project-name>/Scenarios/<scenario-name>/pyPlotList

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

- "Export Format":  Set to "csv" or "feather"
- "Export Compression":  Set to true or false.
- "Export Elements":  Set to true to export static element parameters.


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

.. code-block:: python

    from PyDSS.pydss_results import PyDssResults, ValuesByPropertyAcrossElementsResults

    path = "."
    results = PyDssResults(path)
    scenario = results.scenarios[0]
    # Show the element classes and properties for which data was collected.
    for elem_class in scenario.list_element_classes():
        for prop in scenario.list_element_properties(elem_class):
            for name in scenario.list_element_names(elem_class, prop):
                print(elem_class, prop, name)

    # Read a dataframe for one element.
    df = scenario.get_dataframe("Lines", "Currents", "Line.pvl_112")
    df.head()

                                                  Line.pvl_112__Currents__1A                        Line.pvl_112__Currents__2A
    timestamp
    2017-01-01 00:15:00  (3.5710399970412254e-08+1.3782673590867489e-05j)  (-3.637978807091713e-12+1.1368683772161603e-13j)
    2017-01-01 00:30:00  (3.3905962482094765e-08+1.3793145967611053e-05j)                           1.1368683772161603e-13j
    2017-01-01 00:45:00   (3.381501301191747e-08+1.3786106705993006e-05j)                       (-3.637978807091713e-12+0j)
    2017-01-01 01:00:00  (3.4120603231713176e-08+1.3804576042275585e-05j)   (3.637978807091713e-12+1.1368683772161603e-13j)
    2017-01-01 01:15:00   (3.356035449542105e-08+1.3810414088766265e-05j)  (-3.637978807091713e-12+1.1368683772161603e-13j)

    # Get a dataframe only for terminal 1 conductor A.
    df = scenario.get_dataframe("Lines", "Currents", "Line.pvl_112", label="1A")
    df.head()

                                                   Line.pvl_112__Currents__1A
    timestamp                                                                                       
    2017-01-01 00:15:00  (3.5710399970412254e-08+1.3782673590867489e-05j)
    2017-01-01 00:30:00  (3.3905962482094765e-08+1.3793145967611053e-05j)
    2017-01-01 00:45:00   (3.381501301191747e-08+1.3786106705993006e-05j)
    2017-01-01 01:00:00  (3.4120603231713176e-08+1.3804576042275585e-05j)
    2017-01-01 01:15:00   (3.356035449542105e-08+1.3810414088766265e-05j)


# Welcome to the PyDSS Repository!

**PyDSS** is a high level python interface for **OpenDSS** and provides the following functionalities

**1] Object oriented programming -** OpenDSS is a text based simulation environment. To improve upon the usability of the Python interface, PyDSS wraps each element (PD elements, PC elements, Bus and Circuits) as a object in python. Each of these objects have functions that facilitate 

**2]	Dynamic visualization -** PyDSS uses **Bokeh** to render dynamic plots during simulation runs. The current version includes six plots. These include
	
	 - time series plots
	 - XY plots
	 - Voltage distance plots
	 - Topology plots
	 - GIS overlay plots
	 - Histograms
**3]	Custom controls -**  The main idea behind PyDSS was to come up with a modular approach for adding custom controls to model real systems. New controllers can be added to PyDSS using very little effort. The tool uses outer loop iteration to converge to a steady state solution.
 
 **4]	Simulation parallelization -** PyDSS also facilitates simulating multiple scenarios in parallel thus reducing total computation time
 
  **5]	Exporting results -**  The tool provides multiple options for exporting simulation results. These include options like exporting as a single file or separate files, exporting by element or by class etc.
 
 **6]	Improved Error logging -**  The tool uses a custom logger that can be used to efficiently debug errors 


# Installations requirements

The code has been test using Python 3.6+ and requires installation of a number of additional libraries. The code has been tested using Bokeh version 0.12.5 and can be installed using

 **-pip install bokeh==0.12.5**
 
 All other requirements can be satisfied by installing a Python package like **Anaconda**.




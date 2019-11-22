Enhanced result export features
===============================

PyDSS provides users with high level options to export results and variables of interest. Within the Scenario_settings.TOML file there are four settings users are able to change

.. code-block:: python
	
	"Log Results" = true
	"Return Results" = false
	"Export Mode" = "byClass"
	"Export Style" = "Single file"

- Log Results- [Bool] - Set true if results need to be exported.
- Return Results- [Bool] - Set true if running PyDSS in Cosimulation environment, dssInstance.RunStep() function will return current system states.
- Export Mode- [Str] - Possible options "byClass" and "byElement"
	+ "byClass" option allows user to export specified variable for each element of a particular class e.g. per unit voltage for all bus or active power losses for each line
	+ "byElement" option allows user to export specific results results for each element seperately.
- Export Style- [Str] - possible options "Single_file" and "Separate_files"
	+ "Single_file" merges results to a single file 
	+ "Separate_files" alternately exports results to seperate files.
	
The results to be exported need to defined within the 'ExportLists.json' file for each scenario. the defination file should contain three tables 

- ExportMode-byClass (Needed only if exporting results 'byClass')
- ExportMode-byElement (Needed only if exporting results 'byElement')
- Helics-Subcriptions (Needed only if interfacing with HELICS in a co-simulation environment)
	
.. csv-table:: A example of export definations for ExportMode-byClass
   :file: ExportMode-byClass.csv
   :header-rows: 1
   
- First column of the table needs to be a element type in OpenDSS. The definations here are case sensitive so make sure the name convention for the classes follows case convertion in the OpenDSS help file.
- The second header in the table should always be 'Publish'. This booleam propoerty is used to filter variable that should be published when using the HELICS interface. 
- All other columns sould contain variable names that need to be exportred. PyDSS wraps around each OpenDSS elements and provides high hevel functions that can be used to extract any information pertaining to an element.
	+ For any element propoerty listed in http://dss-extensions.org/OpenDSSDirect.py/opendssdirect.html#module-opendssdirect.CktElement use the exact function name to access that value. Make sure case matches.
	+ For element spicific properties e.g 'Tap' in http://dss-extensions.org/OpenDSSDirect.py/opendssdirect.html#module-opendssdirect.Transformers use lower case convertion. In this case it would be 'tap' as shown in the example above.
	+ Any number of properties may be exported for a class by addeding additional columns
	
.. csv-table:: A example of export definations for ExportMode-byElement
   :file: ExportMode-byElement.csv
   :header-rows: 1
		
- The first column this case should contain complete name of an element defined in OpenDSS model. 
	+ Class name should follow convention defined for 'ExportMode-byClass' definations.
	+ Element name should always be lower case.
- File format for the rest of the table follows the convention defined in for 'ExportMode-byClass' definations.

For setting up sucscription when doing co-simulation via HELICS, 

.. csv-table:: Defining sucscriptions for the HELICS interface
   :file: Helics-Subcriptions.csv
   :header-rows: 1

- The first colun should contain a list of element names defined in the OpenDSS model. Naming converion follows the ExportMode-byElement convertion.
- The second columns defined the property of teh element tat will be updated. This should always be lower case.
- The third column should contain subscription ID and the forth column should define units. Helics allows user to define units that ensure pyhsical values are not connected incorrectly e.g a power variable is not connected to a voltage variable. The federate publishing the IDs should also be defing the units. for more information visit https://helics.readthedocs.io/en/latest/introduction/index.html.
- The subscribe column is used to filter IDs that will be subscribed for a given scenario.
- The final columns defines the expect data type for a given subscription. Possible values are [double, vector, string, boolean, integer]
	
Once defined correctly, after a simulation run, results will be exported to the 'Exports' folder within the project. PyDSS will also intelligently time stamp the results along with assigning units to the exported results. A sample export output is shown below.

.. csv-table:: Exported feeder active and reactive power consumption
   :file: Circuits-TotalPower-1-1.csv
   :header-rows: 1
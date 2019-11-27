Default simulation settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: Scenario_settings.toml
   :language: TOML
   
- Log Results- [Bool] - Set true if results need to be exported
- Return Results- [Bool] - Set true if running PyDSS in Cosimulation environment, RunStep function will return current system states
- Export Mode- [Str] - Possible options "byClass" and "byElement"
- Export Style- [Str] - possible options "Single_file" and "Separate_files"
- Create dynamic plots- [Bool] - Enable rendering of dynamic plots using bokeh
- Open plots in browser- [Bool] - Open plots  in s window. Will work if "Create dynamic plots" is set to true 
- Simulation Type- [String] - Possible options "QSTS", "Dynamic" and "Snapshot"
- Start Year- [Int] - Start year for the simulation study (em nb .g 2017)
- Start Day- [Int] - Start day for the simulation study. Index start at 1
- Start Time (min)- [Float] - Start time in minutes. Floating number can be used to account for second or sub second time points
- End Day- [Float] - End day for the simulation study
- End Time (min)- [Float] - end time in minutes
- Date offset- [Int] - Date offset to be added incase OpenDSS profiles do not start at the begining of the year 
- Step resolution (sec)- [Float] - Time step resolution in seconds
- Max Control Iterations- [Int] - Maximum outer loop control iterations
- Error tolerance- [Float] - Error tolerance in per unit
- Control mode- [String] - Control mode options are "STATIC" or "Time"
- Disable PyDSS controllers- [Bool] - Disable all pyController in PyDSS. All controller implemented in DSS files will still work.
- Active Project- [String] - Name of project to run
- Active Scenario- [String] - Project scenario to use
- DSS File- [String] - The main OpenDSS file
- Co-simulation Mode - [Bool] - Set to true to enable Helics interface all other co-simulation settings only valid if this value is true
- Federate name - [str] - Name of the federate 
- Time delta - [float] - The property controlling the minimum time delta for a federate
- Core type - [str] - Core tyoe to be used for communication
- Uninterruptible - [Bool] - Can the federate be interepted
- Helics logging level - [int] - log
- Enable frequency sweep- [Bool] - Enable harmonic sweep. works with only 'Static' and 'QSTS' simulation modes
- Fundamental frequency- [Float] - Fundamental system frequeny in Hertz
- Start frequency- [Float] - as multiple of fundamental frequency
- End frequency- [Float] - as multiple of fundamental frequency
- Frequency increment- [Float] - as multiple of fundamental 
- Neglect shunt admittance- [Bool] - Neglect shunt addmittance for frequency sweep
- Percentage load in series- [Float] - Percent of load that is series RL for Harmonic studies
- Logging Level- [String] - possible options "DEBUG", "INFO", "WARNING" or "ERROR"
- Log to external file- [Bool] - Boolean variable
- Display on screen- [Bool] - Boolean variable
- Clear old log file- [Bool] - Boolean variable
- Number of Monte Carlo scenarios- [Int] -  Should be set to -1 to disbale MC simulation mode

Default visualization settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   
.. literalinclude:: Batch_settings.toml
   :language: TOML 
   
- [Simulations].Run_simulations-  [Bool] - Run the simulation or not
- [Simulations].Generate_visuals- [Bool] - Create comparative plots. If Run_simulations is false, simulation results from older simulation results will be used if available. If no results are available, an assertion error will be raied.   
- [Simulations].Run_bokeh_server- [Bool] - Run bokeh server. Will only work if Run_simulations Run_bokeh_server = false 
- [Plots].<any plot type>- [Bool] - Enable plots to be created for the given list of scenarios.   
- [Visualization].Plotting_mode- [Str]- possible_values 'Single', 'Separate'
- [Visualization].FileType - [Str]- possible_values 'png', 'pdf'
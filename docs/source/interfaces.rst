Within the example folder the project named external interfaces provides an example usage of all three interafces.

The socket interface
^^^^^^^^^^^^^^^^^^^^

The socket interface is implemented as a PyDSS pyController. Implmentation details and expected inputs are detailed here: :ref:`Socket controller`. The socket controller is weill suited in situatons where an existing controller needs to be integrated to the simulation environment. An exmaple of this would be integrating a controller for thermostatically controlled loads implemeted in say Modelica or Python. This allows user to integrate controller, without making changes to the implemented controller. With a little effort, the same controller can be implemented as a pyController object in PyDSS.

The socket interface in PyDSS also come in handy, when setting up a hardware-in-loop type simulations and integrating the simulation engine with actual hardware. Interfaces similar to raw socket implementations have been developed (to be  open-sourced at a time) for Modbus-TCP and DNP3 communcations have developed and tested with PyDSS with sucess. A minimal socket interfacing example has been provided as a PyDSS project in ~PyDSS/exmaples/External_interfacing_example. Within the folder, ~/PyDSS/examples/External_interfacing_example/pyDSS_project a scenario called 'socket_interface' has been defined. Socket contntroller definations have been detailed with the 'pyControllerList' folder.

.. csv-table:: A example implementation SocketController definations
   :file: SocketController.csv
   :header-rows: 1

In this example, each iteration, voltage and power information is being exported via the socket and new value recieved is used to update the 'kW' property of the load. Once the inputs, outputs, IP and port have been defined, the next step is to create a TOML file and define simulation settings. 

.. code-block:: python

	"Project Path" = "C:\\Users\\alatif\\Desktop\\PyDSS\\examples\\External_interfacing_example"
	"Simulation Type" = "QSTS"
	"Active Project" = "pyDSS_project"
	"Active Scenario" = "socket_interface"
	"DSS File" = "Master_Spohn_existing_VV.dss"


A small script is used to run the particular scenario.

.. code-block:: python

	import click
	import sys
	import os

	@click.command()
	@click.option('--pydss_path',
				  default=r'C:\Users\alatif\Desktop\PyDSS')
	@click.option('--sim_path',
				  default=r'C:\Users\alatif\Desktop\PyDSS\examples\External_interfacing_example\pyDSS_project\PyDSS Scenarios')
	@click.option('--sim_file',
				  default=r'socket_interface.toml') #The TOML file contains simulation settings for the particular scenario
	def run_pyDSS(pydss_path, sim_path, sim_file):
		sys.path.append(pydss_path)
		sys.path.append(os.path.join(pydss_path, 'PyDSS'))
		from pyDSS import instance as dssInstance
		a = dssInstance()                           #Create an instance of PyDSS
		a.run(os.path.join(sim_path, sim_file))     #Run the simulation 

	run_pyDSS()


Finally, the minimal example below shows how to retrive data from the sockets and return new values for parameters defined in the definations file.

.. code-block:: python	
	
	# first of all import the socket library
	import socket
	import struct

	# next create a socket object
	sockets = []
	for i in range(2):
		s = socket.socket()
		s.bind(('127.0.0.1', 5001 + i))
		print("socket binded to %s" % (5001 + i))
		s.listen(5)
		sockets.append(s)
	while True: 
		# Establish connection with client.
		conns = []
		for s in sockets: 
			c, addr = s.accept()
			conns.append(c)
			print('Got connection from', addr)
		while True:
			for c in conns: #Reading data from all ports
				Data = c.recv(1024)
				if Data: #Creating a list of doubles from the recieved byte stream
					numDoubles = int(len(Data) / 8)
					tag = str(numDoubles) + 'd'
					Data = list(struct.unpack(tag, Data))
					print(Data)

			for c , v in zip(conns, [5, 3]): #Writing data to all ports
				values = [v]
				c.sendall(struct.pack('%sd' % len(values), *values))



The HELICS interface
^^^^^^^^^^^^^^^^^^^^

Hierarchical Engine for Large-scale Infrastructure Co-Simulation (HELICS) provides an open-source, general-purpose, modular, highly-scalable co-simulation framework that runs cross-platform (Linux, Windows, and Mac OS X). It is not a modeling tool by itself, but rather an integration tool that enables multiple existing simulation tools (and/or multiple instances of the same tool), known as "federates," to exchange data during runtime and stay synchronized in time such that together they act as one large simulation, or "federation". This enables bringing together established (or new/emerging) off-the-shelf tools from multiple domains to form a complex software-simulation without having to change the individual tools (known as "black-box" modeling). All that is required is for someone to write a thin interface layer for each tool that interfaces with existing simulation time control and data value updating, such as through an existing scripting interface. Moreover, the HELICS community has a growing ecosystem of established interfaces for popular tools, such that many users can simply mix and match existing tools with their own data and run complex co-simulations with minimal coding. More information on HELICS can be found here (https://github.com/GMLC-TDC/HELICS).

The HELICS interface for PyDSS is built to reduuce complexity of setting up large scale cosimulation scenarios. The user is requuired to publications and suscriptions. Details on the formathave been detailed here: :ref:`Enhanced result export features` 

A minimal HELICS interfacing example has been provided as a PyDSS project in ~PyDSS/exmaples/External_interfacing_example. Within the folder, ~PyDSS/examples/External_interfacing_example/pyDSS_project a scenario called ‘helics_interface’ has been defined. Enabling the HELICS interface requires user to define additional patammeters in the scenario TOML file.

.. code-block:: python	

	"Project Path" = "C:\\Users\\alatif\\Desktop\\PyDSS\\examples\\External_interfacing_example"
	"Simulation Type" = "QSTS"
	"Active Project" = "pyDSS_project"
	"Active Scenario" = "helics_interface"
	"DSS File" = "Master_Spohn_existing_VV.dss"
	"Co-simulation Mode" = true 
	"Federate name" = "PyDSS" 
	
- "Co-simulation Mode" : Set to 'true' to enable the HELICS interface. By default it is set to 'false'
- "Federate name" : Required to identify a federate ina cosimulation with a large number of federates.	

Default values for additional simulation settings are as follows. For more information on how to appropriately set these values please look at HELICS documentaion 

.. code-block:: python	

	"Time delta" = 0.01
	"Core type" = "zmq"
	"Uninterruptible" = true
	"Helics logging level" = 5   


For a helics example a minimal dummy federate has been defined using the HELICS Python interaface. The dummy federate script creates a broker and a federate. The federate subsscribes to feeder total power and publishes actie power values for three loads in the network.

.. code-block:: python	

	import time
	import helics as h
	from math import pi
	import random

	initstring = "-f 2 --name=mainbroker"
	fedinitstring = "--broker=mainbroker --federates=1"
	deltat = 0.01

	helicsversion = h.helicsGetVersion()

	print("PI SENDER: Helics version = {}".format(helicsversion))

	# Create broker #
	print("Creating Broker")
	broker = h.helicsCreateBroker("zmq", "", initstring)
	print("Created Broker")

	print("Checking if Broker is connected")
	isconnected = h.helicsBrokerIsConnected(broker)
	print("Checked if Broker is connected")

	if isconnected == 1:
		print("Broker created and connected")

	# Create Federate Info object that describes the federate properties #
	fedinfo = h.helicsCreateFederateInfo()

	# Set Federate name #
	h.helicsFederateInfoSetCoreName(fedinfo, "Test Federate")

	# Set core type from string #
	h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "zmq")

	# Federate init string #
	h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)

	# Set the message interval (timedelta) for federate. Note th#
	# HELICS minimum message time interval is 1 ns and by default
	# it uses a time delta of 1 second. What is provided to the
	# setTimedelta routine is a multiplier for the default timedelta.

	# Set one second message interval #
	h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)

	# Create value federate #
	vfed = h.helicsCreateValueFederate("Test Federate", fedinfo)
	print("PI SENDER: Value federate created")

	# Register the publication #
	pub1 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.power", "double", "kW")
	print("PI SENDER: Publication registered")
	pub2 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load2.power", "double", "kW")
	print("PI SENDER: Publication registered")
	pub3 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load3.power", "double", "kW")
	print("PI SENDER: Publication registered")
	sub1 = h.helicsFederateRegisterSubscription(vfed, "Circuit.heco19021.TotalPower.E", "kW")
	# Enter execution mode #
	h.helicsFederateEnterExecutingMode(vfed)
	print("PI SENDER: Entering execution mode")

	# This federate will be publishing deltat*pi for numsteps steps #

	for t in range(0, 96):
		currenttime = h.helicsFederateRequestTime(vfed, t * 15 * 60)
		h.helicsPublicationPublishDouble(pub1, 5.0)
		h.helicsPublicationPublishDouble(pub2, -1.0)
		h.helicsPublicationPublishDouble(pub3, random.random() * 12)

		value = h.helicsInputGetString(sub1)
		print(
			"Circuit active power demand: {} kW @ time: {}".format(
				value, currenttime
			)
		)

		time.sleep(0.01)

	h.helicsFederateFinalize(vfed)
	print("PI SENDER: Federate finalized")

	while h.helicsBrokerIsConnected(broker):
		time.sleep(1)

	h.helicsFederateFree(vfed)
	h.helicsCloseLibrary()

	print("PI SENDER: Broker disconnected")

The API interface
^^^^^^^^^^^^^^^^^

Using the API interface gives user access to results within the result contianar. would require user to create an instance of the :class:`PyDSS.dssInstacne` class. This would require the user to define the arguments dictionary. If structured correctly, user should be able to invove an instance of PyDSS. Ensure within the passed arguments dictionary, 

.. code-block:: python

	"Return Results" : True

Else, None will be returned at simulator steps through time. Once an instance has been created, simulation may be controlled externaly. A simple example is as follows:


A minimal HELICS interfacing example has been provided as a PyDSS project in ~PyDSS/exmaples/External_interfacing_example. Within the folder, ~PyDSS/examples/External_interfacing_example/pyDSS_project a scenario called ‘API_interface’ has been defined. Enabling the HELICS interface requires user to define additional patammeters in the scenario TOML file.

.. code-block:: python

	import click
	import sys
	import os

	@click.command()
	@click.option('--pydss_path',
				  default=r'C:\Users\alatif\Desktop\PyDSS')
	@click.option('--sim_path',
				  default=r'C:\Users\alatif\Desktop\PyDSS\examples\External_interfacing_example\pyDSS_project\PyDSS Scenarios')
	@click.option('--sim_file',
				  default=r'api_interface.toml')
	@click.option('--run_simulation',
				  default=True)
	@click.option('--generate_visuals',
				  default=False)
	def run_pyDSS(pydss_path, sim_path, sim_file, run_simulation, generate_visuals):
		sys.path.append(pydss_path)
		sys.path.append(os.path.join(pydss_path, 'PyDSS'))
		from pyDSS import instance as dssInstance
		a = dssInstance() # Create an instance of PyDSS
		sim_args = a.update_scenario_settigs(os.path.join(sim_path, sim_file)) # Update the default settings
		dssInstance = a.create_dss_instance(sim_args)  
		for t in range(5): # Run simulation for five time steps
			x = {'Load.mpx000635970':{'kW':7.28}} 
			results = dssInstance.RunStep(t, x) # Update the value of a load
			print(results['Load.mpx000635970']['Powers']['E']['value'])  Update the new value of the load
		dssInstance.ResultContainer.ExportResults() # Export the results
		dssInstance.DeleteInstance()
		del a
	run_pyDSS()



	
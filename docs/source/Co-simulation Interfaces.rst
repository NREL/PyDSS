

The HELICS interface
^^^^^^^^^^^^^^^^^^^^


Hierarchical Engine for Large-scale Infrastructure Co-Simulation (HELICS) provides an open-source, general-purpose, modular, highly-scalable co-simulation framework that runs cross-platform (Linux, Windows, and Mac OS X). It is not a modeling tool by itself, but rather an integration tool that enables multiple existing simulation tools (and/or multiple instances of the same tool), known as "federates," to exchange data during runtime and stay synchronized in time such that together they act as one large simulation, or "federation". This enables bringing together established (or new/emerging) off-the-shelf tools from multiple domains to form a complex software-simulation without having to change the individual tools (known as "black-box" modeling). All that is required is for someone to write a thin interface layer for each tool that interfaces with existing simulation time control and data value updating, such as through an existing scripting interface. Moreover, the HELICS community has a growing ecosystem of established interfaces for popular tools, such that many users can simply mix and match existing tools with their own data and run complex co-simulations with minimal coding. More information on HELICS can be found here (https://github.com/GMLC-TDC/HELICS).

The HELICS interface for pydss is built to reduce complexity of setting up large scale cosimulation scenarios. The user is required to publications and suscriptions.

A minimal HELICS example is availble in the ``examples`` folder (top directory of the repository). Enabling the HELICS interface requires user to define additional parammeters in the scenario TOML file.


Interface overview
---------------------------

The HELICS interface can be enabled and setup using the simultion.toml file. 

Following attributes can be configured for the HELICS interface.

.. autopydantic_model:: pydss.simulation_input_models.HelicsModel

	
- "co_simulation_mode" : Set to 'true' to enable the HELICS interface. By default it is set to 'false'
- "federate_name" : Required to identify a federate in a cosimulation with a large number of federates.	
- Additional attribution pertaining to convergence, timing and iteration can be configured here

Default values for additional simulation settings are as follows. For more information on how to appropriately set these values please look at HELICS documentaion 

Once the HELICS co-simulation interface has been enabled, the next step is to set up ``publications`` and ``subscriptions`` to set up information exchange with external federates. 
Pydss enables zero code setup of these modules. Each scenario can have its publlcation and subscription defination and is managed by two file in the ``ExportLists`` directory for a given scenario.

publication tags (names) follow the following convertion

.. code-block::

	<federate name>.<object type>.<object name>.<object property>

	examples,

	federate1.Circuit.70008.TotalPower
	federate1.Load.load_1.VoltageMagAng

where ``federate name`` is defined in the project's ``settings.toml`` file

Setting up publications
---------------------------
Publications (information communicated to external federates) can be set up by using the ``Exports.toml``. This file is also used to define export varibles 
for a simulation scenario. By setting the ``publish`` attribute to ``true``, enable automated setup of a HELICS publication. 
The file enables users to use multiple filtering options such as regex operation etc. to only pushlish what is reuired for a given use case.

examples:

The following code block will setup publications for all PV systems powers in a given model. 
Setting the ``publish`` attribute to ``false`` will allow the data to be writtin to the h5 store, 
but the data will not be published on the helics interface.

.. code-block:: toml	

	[[PVSystems]]
	property = "Powers"
	sample_interval = 1
	publish = true
	store_values_type = "all"

Users tave two options to filter and setup publication for a subset of object type (in this case PV systems). 
User are able to use tag attribute ``name_regexes`` to filter PV systems matching a given list of regex expressions.
Alternately, users can use ``names`` attribute to explicitly define objects whos property they want publiched on the HELICS interface.

Filtering using regex expressions

.. code-block:: toml

	[[PVSystems]]
	property = "Powers"
	name_regexes = [".*pvgnem.*"]
	sample_interval = 1
	publish = true
	store_values_type = "all"

Filtering using explicitly list model names 

.. code-block:: toml

	[[PVSystems]]
	property = "Powers"
	sample_interval = 1
	names = ["PVSystems.pv1", "PVSystems.pv2"]
	publish = true
	store_values_type = "all"



Setting up subscriptions
---------------------------

Subscriptions (information ingested from external federates) can be set up 
using the ``Subscriptions.toml`` in the ``ExportLists`` directory for a given scenario.
Valis subscriptions should confine to teh following model

.. autopydantic_model:: pydss.helics_interface.Subscription

When setting up subscriptions it is important to understand that the subscription tag is generated by 
the external federate and should be known before setting up the subscriptions. In the example below, values recieved from
subscription tag ``test.load1.power`` are used to update the ``kw`` property of load ``Load.mpx000635970``. ``multiplier`` property can be used to
scale values before they are used to update the coupled model. 

example

.. code-block:: toml

	[[subscriptions]]
	model = "Load.mpx000635970"
	property = "kw"
	id = "test.load1.power"
	unit = "kW"
	subscribe = true
	data_type = "double"
	multiplier = 1 


Within the example folder the project named external interfaces provides an example usage of all three interafces.

The socket interface
^^^^^^^^^^^^^^^^^^^^

The socket interface is implemented as a pydss pyController. Implmentation details and expected inputs are detailed here: :py:class:`pydss.pyControllers.Controllers.SocketController.SocketController`. 
The socket controller is well suited in situatons where an existing controller needs to be integrated to the simulation environment. 
An exmaple of this would be integrating a controller for thermostatically controlled loads implemeted in say Modelica or Python. 
This allows user to integrate controller, without making changes to the implemented controller. With a little effort, 
the same controller can be implemented as a pyController object in pydss.

The socket interface in pydss also come in handy, when setting up a hardware-in-loop type simulations and integrating the simulation 
engine with actual hardware. Interfaces similar to raw socket implementations have been developed (to be  open-sourced at a later time) 
for Modbus-TCP and DNP3 communcations have developed and tested with pydss with sucess. A minimal socket interfacing example has 
been provided as a pydss project in ~pydss/examples/external_interfaces. Within the folder, 
~/pydss/examples/external_interfaces/pydss_project a scenario called 'socket' has been defined. Socket 
controller definations have been detailed with the 'pyControllerList' folder. An example of input requirements can be studied below.
This example will publish ``voltage magnitude`` (see Even set in Index) and ``real power`` for load ``Load.mpx000635970`` in the model. Subscribed 
values will be used to update the ``kW`` property of the coupled load (Load.mpx000635970 in this case)

.. code-block:: toml

	["Load.mpx000635970"]
	IP = "127.0.0.1"
	Port = 5001
	Encoding = false
	Buffer = 1024
	Index = "Even,Even"
	Inputs = "VoltagesMagAng,Powers"
	Outputs = "kW"


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
		s.listen(5)
		sockets.append(s)
	while True: 
		# Establish connection with client.
		conns = []
		for s in sockets: 
			c, addr = s.accept()
			conns.append(c)
		while True:
			for c in conns: #Reading data from all ports
				Data = c.recv(1024)
				if Data: #Creating a list of doubles from the recieved byte stream
					numDoubles = int(len(Data) / 8)
					tag = str(numDoubles) + 'd'
					Data = list(struct.unpack(tag, Data))
			for c , v in zip(conns, [5, 3]): #Writing data to all ports
				values = [v]
				c.sendall(struct.pack('%sd' % len(values), *values))





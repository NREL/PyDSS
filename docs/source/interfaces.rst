Within the example folder the project named external interfaces provides an example usage of all three interafces.

The socket interface
^^^^^^^^^^^^^^^^^^^^

The socket interface is implemented as a PyDSS pyController. Implmentation details and expected inputs are detailed here: :ref:`Socket controller` 

The HELICS interface
^^^^^^^^^^^^^^^^^^^^

The HELICS interface is implemented within the . Implmentation details and expected inputs are detailed here: :ref:`Socket controller`. Setting up the interface required users define parameters that have been detailed here: :ref:`Enhanced result export features` 


The API interface
^^^^^^^^^^^^^^^^^

Using the API interface would require user to create an instance of the :class:`PyDSS.dssInstacne` class. This would require the user to define the arguments dictionary. If structured correctly, user should be able to invove an instance of PyDSS. Ensure within the passed arguments dictionary, 

.. code-block:: python

	"Return Results" : True

Else, None will be returned at simulator steps through time. Once an instance has been created, simulation may be controlled externaly. A simple example is as follows:


.. code-block:: python

	def run_simulation(args_dict):
		results = []
		simulator = PyDSS.dssInstance(args_dict)
		for i in range(10):
			results.append(simulator.RunStep(stepSize))
		simulator.DeleteInstance()
		return results
	
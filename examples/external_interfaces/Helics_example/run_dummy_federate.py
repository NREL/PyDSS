# -*- coding: utf-8 -*-
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
#h.helicsFederateInfoSetIntegerProperty(fedinfo, h.helics_property_int_log_level, 20)
# Create value federate #
vfed = h.helicsCreateValueFederate("Test Federate", fedinfo)
print("PI SENDER: Value federate created")

# Register the publication #
pub1 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.power", "double", "kW")

print("PI SENDER: Publication registered")
pub2 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.feederhead.voltage", "double", "kW")
print("PI SENDER: Publication registered")
sub1 = h.helicsFederateRegisterSubscription(vfed, "PyDSS.PVSystem.pvgnem_mpx000635970.Powers", "kW")
#h.helicsInputSetMinimumChange(sub1, 0.1)

# Enter execution mode #
h.helicsFederateEnterExecutingMode(vfed)


for t in range(1, 5):
    time_requested = t * 15 * 60
    #while time_requested < r_seconds:
    currenttime = h.helicsFederateRequestTime(vfed, time_requested)
    iteration_state = h.helics_iteration_result_iterating
    for i in range(20):
        currenttime, iteration_state = h.helicsFederateRequestTimeIterative(
            vfed,
            time_requested,
            h.helics_iteration_request_iterate_if_needed
        )
        h.helicsPublicationPublishDouble(pub1, 5.0 + 1. / (1.0 + i))
        print("Published: {}".format((5.0 + 1. / (1.0 + i))))
        h.helicsPublicationPublishDouble(pub2, 1.0)
        value = h.helicsInputGetString(sub1)
        print("Circuit active power demand: {} kW @ time: {}".format(value, currenttime))
        #time.sleep(0.01)
        #i+=1
    time.sleep(0.1)


h.helicsFederateFinalize(vfed)
print("PI SENDER: Federate finalized")

while h.helicsBrokerIsConnected(broker):
    time.sleep(1)

h.helicsFederateFree(vfed)
h.helicsCloseLibrary()

print("PI SENDER: Broker disconnected")
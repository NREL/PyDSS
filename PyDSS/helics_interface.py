from PyDSS.pyContrReader import pyExportReader, pySubscriptionReader
from PyDSS.pyLogger import getLoggerTag
import logging
import helics
import os

class helics_interface():
    type_info = {
        'CurrentsMagAng': 'vector',
        'Currents': 'vector',
        'RatedCurrent': 'double',
        'EmergAmps': 'double',
        'NormalAmps': 'double',
        'normamps': 'Amp',
        'Losses': 'vector',
        'PhaseLosses': 'vector',
        'Powers': 'vector',
        'TotalPower': 'vector',
        'LineLosses': 'vector',
        'SubstationLosses': 'vector',
        'kV': 'double',
        'kVARated': 'double',
        'kvar': 'double',
        'kW': 'double',
        'kVABase': 'double',
        'kWh': 'double',
        'puVmagAngle': 'vector',
        'VoltagesMagAng': 'vector',
        'VMagAngle': 'vector',
        'Voltages': 'vector',
        'Vmaxpu': 'double',
        'Vminpu': 'double',
        'Frequency': 'double',
        'Taps': 'vector',
        '%stored': 'double',
        'Distance': 'double'
    }

    def __init__(self, dss_solver, objects_by_name, objects_by_class, options, system_paths):

        if options["Logging"]["Pre-configured logging"]:
            LoggerTag = __name__
        else:
            LoggerTag = getLoggerTag(options)
        self._logger = logging.getLogger(LoggerTag)
        self._options = options
        self._publications = {}
        self._subscriptions = {}
        self._system_paths = system_paths
        self._objects_by_element = objects_by_name
        self._objects_by_class = objects_by_class
        self._create_helics_federate()
        self._dss_solver = dss_solver
        self._registerFederateSubscriptions()
        self._registerFederatePublications()
        helics.helicsFederateEnterExecutingMode(self._PyDSSfederate)
        self._logger.info('Entered HELICS execution mode')

    def _create_helics_federate(self):
        fedinfo = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreName(fedinfo, self._options['Helics']['Federate name'])
        helics.helicsFederateInfoSetCoreTypeFromString(fedinfo, self._options['Helics']['Core type'])
        helics.helicsFederateInfoSetCoreInitString(fedinfo, f"--federates=1")
        #helics.helicsFederateInfoSetBroker(fedinfo, self._options['Helics']['Broker'])
        #helics.helicsFederateInfoSetBrokerPort(fedinfo, self._options['Helics']['Broker port'])
        helics.helicsFederateInfoSetTimeProperty(fedinfo, helics.helics_property_time_delta,
                                                 self._options['Helics']['Time delta'])
        helics.helicsFederateInfoSetIntegerProperty(fedinfo, helics.helics_property_int_log_level,
                                                self._options['Helics']['Helics logging level'])

        helics.helicsFederateInfoSetFlagOption(fedinfo, helics.helics_flag_uninterruptible, True)
        self._PyDSSfederate = helics.helicsCreateValueFederate(self._options['Helics']['Federate name'], fedinfo)
        return


    def _registerFederateSubscriptions(self):
        self._sub_file_reader = pySubscriptionReader(
            os.path.join(
                self._system_paths["ExportLists"],
                "Subscriptions.toml",
            ),
        )
        self._subscriptions = {}
        for element, subscription in self._sub_file_reader.SubscriptionList.items():
            assert element in self._objects_by_element, '"{}" listed in the subscription file not '.format(element) +\
                                                     "available in PyDSS's master object dictionary."

            sub = helics.helicsFederateRegisterSubscription(
                self._PyDSSfederate,
                subscription["Subscription ID"],
                subscription["Unit"]
            )
            self._logger.info('Subscription registered: "{}" with units "{}"'.format(
                subscription["Subscription ID"],
                subscription["Unit"])
            )
            subscription['Subscription'] = sub
            self._subscriptions[element] = subscription
        return

    def updateHelicsSubscriptions(self):
        for element_name, sub_info in self._subscriptions.items():
            if 'Subscription' in sub_info:
                value = None
                if sub_info['Data type'].lower() == 'double':
                    value = helics.helicsInputGetDouble(sub_info['Subscription'])
                    print(element_name, value)
                elif sub_info['Data type'].lower() == 'vector':
                    value = helics.helicsInputGetVector(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'string':
                    value = helics.helicsInputGetString(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'boolean':
                    value = helics.helicsInputGetBoolean(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'integer':
                    value = helics.helicsInputGetInteger(sub_info['Subscription'])


                if value:
                    dssElement = self._objects_by_element[element_name]
                    dssElement.SetParameter(sub_info['Property'], value)

                    self._logger.info('Value for "{}.{}" changed to "{}"'.format(
                        element_name,
                        sub_info['Property'],
                        value
                    ))

    def _registerFederatePublications(self):
        self._file_reader = pyExportReader(
            os.path.join(
                self._system_paths ["ExportLists"],
                "ExportMode-byClass.toml",
            ),
        )
        self._publications = {}
        for valid_publication in self._file_reader.publicationList:
            obj_class, obj_property = valid_publication.split(' ')
            objects = self._objects_by_class[obj_class]
            for obj_X, obj in objects.items():
                name = '{}.{}.{}'.format(self._options['Helics']['Federate name'], obj_X, obj_property)
                self._publications[name] = helics.helicsFederateRegisterGlobalTypePublication(
                    self._PyDSSfederate,
                    name,
                    self.type_info[obj_property],
                    ''
                )
                self._logger.info(f'Publication registered: {name}')
        return

    def updateHelicsPublications(self):
        for element, pub in self._publications.items():
            fed_name, class_name, object_name, ppty_name = element.split('.')
            obj_name = '{}.{}'.format(class_name, object_name)
            obj = self._objects_by_element[obj_name]
            value = obj.GetValue(ppty_name)
            if isinstance(value, list):
                helics.helicsPublicationPublishVector(pub, value)
            elif isinstance(value, float):
                helics.helicsPublicationPublishDouble(pub, value)
            elif isinstance(value, str):
                helics.helicsPublicationPublishString(pub, value)
            elif isinstance(value, bool):
                helics.helicsPublicationPublishBoolean(pub, value)
            elif isinstance(value, int):
                helics.helicsPublicationPublishInteger(pub, value)
        return

    def request_time_increment(self):
        if self._options['Helics']['Co-simulation Mode']:
            r_seconds = self._dss_solver.GetTotalSeconds() + self._dss_solver.GetStepResolutionSeconds()
            print('Time: ', self._dss_solver.GetTotalSeconds() )
            c_seconds = 0
            while c_seconds < r_seconds:
                c_seconds = helics.helicsFederateRequestTime(self._PyDSSfederate, r_seconds)
            print('Time requested: ', r_seconds)
            print('Time granted: ', c_seconds)
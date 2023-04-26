from PyDSS.pyContrReader import pyExportReader, pySubscriptionReader
from PyDSS.simulation_input_models import SimulationSettingsModel
from PyDSS.export_list_reader import ExportListReader
from PyDSS.helics_mapping import HELICS_MAPPING
from PyDSS.pyLogger import getLoggerTag
from PyDSS.utils.utils import load_data
from PyDSS.common import ExportMode
from click import pass_context
from re import L
import logging
import helics
import os

class helics_interface:

    n_states = 5
    init_state = 1
    
    ppty_mapping = {
        'CurrentsMagAng': 'current',
        'Currents': 'current',
        'RatedCurrent': 'current',
        'EmergAmps': 'current',
        'NormalAmps': 'normcurrent',
        'normamps': 'current',
        'Losses': 'power',
        'PhaseLosses': 'power',
        'Powers': 'power',
        'TotalPower': 'power',
        'LineLosses': 'power',
        'SubstationLosses': 'power',
        'kV': 'voltage',
        'kVARated': 'power',
        'kvar': 'power',
        'kW': 'power',
        'kVABase': 'power',
        'kWh': 'power',
        'puVmagAngle': 'voltage',
        'VoltagesMagAng': 'voltage',
        'VMagAngle': 'voltage',
        'Voltages': 'voltage',
        'Vmaxpu': 'voltage',
        'Vminpu': 'voltage',
        'Frequency': 'frequency',
        'Taps': 'taps',
        '%stored': 'energy',
        'Distance': 'distance',
        "states": "states",
        "tap": "tap",
    }

    type_info = {
        'CurrentsMagAng': 'vector',
        'Currents': 'vector',
        'RatedCurrent': 'double',
        'EmergAmps': 'double',
        'NormalAmps': 'double',
        'normamps': 'double',
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

    def __init__(self, dss_solver, objects_by_name, objects_by_class, settings: SimulationSettingsModel, system_paths, default=True):
        LoggerTag = getLoggerTag(settings)
        self.itr = 0
        self.c_seconds = 0
        self.c_seconds_old = -1
        self._logger = logging.getLogger(LoggerTag)
        self._settings = settings
        self._co_convergance_error_tolerance = settings.helics.error_tolerance
        self._co_convergance_max_iterations = self._settings.helics.max_co_iterations
        self._publications = {}
        self._subscriptions = {}
        self._system_paths = system_paths
        self._objects_by_element = objects_by_name
        self._objects_by_class = objects_by_class
        self._create_helics_federate()
        self._dss_solver = dss_solver
        if default:
            self.registerPubSubTags()


    def registerPubSubTags(self, pubs=None, subs=None):

        self._registerFederateSubscriptions(subs)
        self._registerFederatePublications(pubs)

        helics.helicsFederateEnterExecutingMode(self._PyDSSfederate)

        # helics.helicsFederateEnterExecutingModeIterative(
        #     self._PyDSSfederate,
        #     helics.helics_iteration_request_iterate_if_needed
        # )
        self._logger.info('Entered HELICS execution mode')

    def _create_helics_federate(self):
        self.fedinfo = helics.helicsCreateFederateInfo()
        helics.helicsFederateInfoSetCoreName(self.fedinfo, self._settings.helics.federate_name)
        helics.helicsFederateInfoSetCoreTypeFromString(self.fedinfo, self._settings.helics.core_type)
        helics.helicsFederateInfoSetCoreInitString(self.fedinfo, f"--federates=1")
        IP = self._settings.helics.broker
        Port = self._settings.helics.broker_port
        self._logger.info("Connecting to broker @ {}".format(f"{IP}:{Port}" if Port else IP))
        if self._settings.helics.broker:
            helics.helicsFederateInfoSetBroker(self.fedinfo, self._settings.helics.broker)
        if self._settings.helics.broker_port:
            helics.helicsFederateInfoSetBrokerPort(self.fedinfo, self._settings.helics.broker_port)
        helics.helicsFederateInfoSetTimeProperty(self.fedinfo, helics.helics_property_time_delta,
                                                 self._settings.helics.time_delta)
        helics.helicsFederateInfoSetIntegerProperty(self.fedinfo, helics.helics_property_int_log_level,
                                                    self._settings.helics.logging_level)
        helics.helicsFederateInfoSetIntegerProperty(self.fedinfo, helics.helics_property_int_max_iterations,
                                                    self._settings.helics.max_co_iterations)
        self._PyDSSfederate = helics.helicsCreateValueFederate(self._settings.helics.federate_name, self.fedinfo)
        return

    def _registerFederateSubscriptions(self, subs):
        """
        :param subs:
        :return:
        """

        if subs is not None:
            SubscriptionList = subs
        else:
            self._sub_file_reader = pySubscriptionReader(
                os.path.join(
                    self._system_paths["ExportLists"],
                    "Subscriptions.toml",
                ),
            )
            SubscriptionList = self._sub_file_reader.SubscriptionList
        self._subscriptions = {}
        self._subscription_dState = {}
        for element, subscription in SubscriptionList.items():
            assert element in self._objects_by_element, '"{}" listed in the subscription file not '.format(element) +\
                                                     "available in PyDSS's master object dictionary."

            sub = helics.helicsFederateRegisterSubscription(
                self._PyDSSfederate,
                subscription["Subscription ID"],
                subscription["Unit"]
            )
            #helics.helicsInputSetMinimumChange(sub, self._settings.helics.error_tolerance)
            self._logger.info('Subscription registered: "{}" with units "{}"'.format(
                subscription["Subscription ID"],
                subscription["Unit"])
            )
            subscription['Subscription'] = sub
            self._subscriptions[element] = subscription
            self._subscription_dState[element] = [self.init_state] * self.n_states
        return

    def updateHelicsSubscriptions(self):

        for element_name, sub_info in self._subscriptions.items():
            if 'Subscription' in sub_info:
                value = None
                if sub_info['Data type'].lower() == 'double':
                    value = helics.helicsInputGetDouble(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'vector':
                    value = helics.helicsInputGetVector(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'string':
                    value = helics.helicsInputGetString(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'boolean':
                    value = helics.helicsInputGetBoolean(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'integer':
                    value = helics.helicsInputGetInteger(sub_info['Subscription'])
                elif sub_info['Data type'].lower() == 'complex':
                    value = helics.helicsInputGetComplex(sub_info['Subscription'])
                
                #todo: remove teh line below
                #value = (value[0]**2+ value[1]**2)**0.5
                print(value)
                value = 1.02
                print(element_name, value)
                if value and value != 0:
                    value = value * sub_info['Multiplier']

                    dssElement = self._objects_by_element[element_name]
                    dssElement.SetParameter(sub_info['Property'], value)

                    self._logger.info('Value for "{}.{}" changed to "{}"'.format(
                        element_name,
                        sub_info['Property'],
                        value * sub_info['Multiplier']
                    ))

                    if self._settings.helics.iterative_mode:
                        if self.c_seconds != self.c_seconds_old:
                            self._subscription_dState[element_name] = [self.init_state] * self.n_states
                        else:
                            self._subscription_dState[element_name].insert(0, self._subscription_dState[element_name].pop())
                        self._subscription_dState[element_name][0] = value
                else:
                    self._logger.warning('{} will not be used to update element for "{}.{}" '.format(
                        value,
                        element_name,
                        sub_info['Property']))
        self.c_seconds_old = self.c_seconds

    def _registerFederatePublications(self, pubs):
        publicationList = None
        self.sPubs = []
        if pubs is not None:
            publicationList= pubs
        else:
            try:
                self._file_reader = pyExportReader(
                    os.path.join(
                        self._system_paths ["ExportLists"],
                        ExportMode.BY_CLASS.value + ".toml",
                    ),
                )
                publicationList = self._file_reader.publicationList
            except:
                try:
                    file =  os.path.join(
                            self._system_paths ["ExportLists"],
                             ExportMode.EXPORTS.value + ".toml",
                        )
                    self._file_reader = ExportListReader( file )
                    publicationList = self._file_reader.publicationList
  

                except:
                    assert publicationList is not None, "PyDSS failed to read publications"

        self._publications = {}
        all_filtered_elements = {}
        for elm_class, elm_ppty_dict in publicationList.items():
            all_filtered_elements[elm_class] = {}
            objects = self._objects_by_class[elm_class]
            for elm_ppty, elm_filter in elm_ppty_dict.items():
                if elm_filter is None:
                    filtered_objects = objects
                elif isinstance(elm_filter, set):
                    filtered_objects = {}
                    for n in elm_filter:
                        if n in objects:
                            filtered_objects[n] = objects[n]
                        else:
                            raise Exception(f"{n} object not found in the OpenDSS model")
                elif isinstance(elm_filter, list):

                    object_names = list(objects.keys())
                    filtered_names = []
                    for r in elm_filter:
                        filtered_list = list(filter(r.match, object_names))
                        filtered_names.extend(filtered_list)

                    filtered_names = list(set(filtered_names))
                    filtered_objects = {}
                    for n in filtered_names:
                        if n in objects:
                            filtered_objects[n] = objects[n]
                        else:
                            raise Exception(f"{n} object not found in the OpenDSS model")
                    pass
                else:
                    raise Exception("Publication dictionary is in an unexpected format.")

                all_filtered_elements[elm_class][elm_ppty] = filtered_objects
        
        for elm_class, ppty_dict in all_filtered_elements.items():
            for ppty, obj_dict in ppty_dict.items():
                for obj_name, obj in obj_dict.items():
                    
                    value = obj.GetValue(ppty, convert=True)
                    htype = self.get_helics_data_type(value.value)                   
                    names = self.creatPublicationName(obj_name, ppty, value.units)
                    hmap = HELICS_MAPPING(obj, ppty, value, self._settings.helics.federate_name)
                    
                    pub_inst = helics.helicsFederateRegisterGlobalTypePublication(
                            self._PyDSSfederate,
                            hmap.pubname,
                            "complex",
                            hmap.units
                        ) 
                    for k, v in hmap.tags.items():
                        helics.helicsPublicationSetTag(pub=pub_inst, tagname=k, tagvalue=v)
                    
                    hmap.pub = pub_inst
                    self.sPubs.append(hmap)
                    self._logger.info(f'Publication registered: {hmap.pubname} with units {hmap.units}')
                   
                    for i, n in enumerate(names):
                        
                        ph_test = n.split("/")[-2]
                        
                        if ph_test != "N":

                            if not isinstance(value.value, list):
                                v = value.value
                            else:
                                v = value.value[i]
                            
                            pubtype = "complex" if isinstance(v, complex) else "double"
                            unit = value.units[i]["unit"]
                            pub =  helics.helicsFederateRegisterGlobalTypePublication(
                                self._PyDSSfederate,
                                n,
                                "complex",
                                unit
                            )
                            self._publications[n] = {
                                "publication": pub,
                                "value_index": i,
                                "pydss_object": obj,
                                "property": ppty,
                                "type": pubtype,
                            }
                            self._logger.info(f'Publication registered: {n} with units {unit}')
        for p in self.sPubs:
            print(p)

    def creatPublicationName(self, obj_name, ppty, units):
        names = []
        for unit in units:
            obj_name = obj_name.replace(".", "/")
            mapped_meas = self.ppty_mapping[ppty]
            name = f"{self._settings.helics.federate_name}/{obj_name}/{mapped_meas}/{unit['type']}/{unit['phase']}/{unit['terminal']}"
            names.append(name)
        return names

    def get_helics_data_type(self, value):
        if isinstance(value, float):
            return helics.HELICS_DATA_TYPE_DOUBLE.name
        elif isinstance(value, str):
            return helics.HELICS_DATA_TYPE_STRING.name
        elif isinstance(value, bool):
            return helics.HELICS_DATA_TYPE_BOOLEAN.name
        elif isinstance(value, int):
            return helics.HELICS_DATA_TYPE_INT.name
        elif isinstance(value, complex):
            return helics.HELICS_DATA_TYPE_COMPLEX.name
        elif isinstance(value, list):
            if isinstance(value[0], complex):
                return helics.HELICS_DATA_TYPE_COMPLEX_VECTOR.name
            else:
                return helics.HELICS_DATA_TYPE_VECTOR.name
        else:
            raise Exception(f"Data type {type(value)} not supported")
        return

    def updateHelicsPublications2(self):
        for helics_map in self.sPubs:
            value = helics_map.value    
            if isinstance(value, float):
                helics.helicsPublicationPublishDouble(helics_map.pub, value)
            elif isinstance(value, str):
                helics.helicsPublicationPublishString(helics_map.pub, value)
            elif isinstance(value, bool):
                helics.helicsPublicationPublishBoolean(helics_map.pub, value)
            elif isinstance(value, int):
                helics.helicsPublicationPublishInteger(helics_map.pub, value)
            elif isinstance(value, complex):
                helics.helicsPublicationPublishComplex(helics_map.pub, value)
            elif isinstance(value, list):
                if isinstance(value[0], complex):
                    helics.helicsPublicationPublishComplexVector(helics_map.pub, value)
                else:
                    helics.helicsPublicationPublishVector(helics_map.pub, value)
        return

    def updateHelicsPublications(self):
        self.updateHelicsPublications2()
        for element, pub_dict in self._publications.items():
            pub = pub_dict["publication"]
            obj = pub_dict["pydss_object"]
            value  = obj.GetValue(pub_dict["property"], convert=True)
            
            value = value.value

            if pub_dict["value_index"] is not None and isinstance(value, list):
                value = value[pub_dict["value_index"]] 

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
            elif isinstance(value, complex):
                helics.helicsPublicationPublishComplex(pub, value)
        return

    def request_time_increment(self):
        error = sum([abs(x[0] - x[1]) for k, x in self._subscription_dState.items()])
        r_seconds = self._dss_solver.GetTotalSeconds() #- self._dss_solver.GetStepResolutionSeconds()
        if not self._settings.helics.iterative_mode:
            while self.c_seconds < r_seconds:
                self.c_seconds = helics.helicsFederateRequestTime(self._PyDSSfederate, r_seconds)
            self._logger.info('Time requested: {} - time granted: {} '.format(r_seconds, self.c_seconds))
            return True, self.c_seconds
        else:

            self.c_seconds, iteration_state = helics.helicsFederateRequestTimeIterative(
                self._PyDSSfederate,
                r_seconds,
                helics.helics_iteration_request_iterate_if_needed
            )

            self._logger.info('Time requested: {} - time granted: {} error: {} it: {}'.format(
                r_seconds, self.c_seconds, error, self.itr))
            if error > -1 and self.itr < self._co_convergance_max_iterations - 1:
                self.itr += 1
                return False, self.c_seconds
            else:
                self.itr = 0
                return True, self.c_seconds

    def __del__(self):
        try:
            helics.helicsFederateFinalize(self._PyDSSfederate)
            state = helics.helicsFederateGetState(self._PyDSSfederate)
            helics.helicsFederateInfoFree(self.fedinfo)
            helics.helicsFederateFree(self._PyDSSfederate)
            self._logger.info('HELICS federate for PyDSS destroyed')
        except:
            pass

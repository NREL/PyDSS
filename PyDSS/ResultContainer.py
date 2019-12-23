from PyDSS.pyContrReader import pySubscriptionReader as pySR
from PyDSS.unitDefinations import type_info as Types
from PyDSS.unitDefinations import unit_info as Units
from PyDSS.pyContrReader import pyExportReader as pyER
from PyDSS import unitDefinations
import pandas as pd
import numpy as np
import helics as h
import pathlib
import logging
import shutil
import math
import os


class ResultContainer:

    def __init__(self, Options, SystemPaths, dssObjects, dssObjectsByClass, dssBuses, dssSolver, dssCommand):
        LoggerTag = Options['Active Project'] + '_' + Options['Active Scenario']
        self.metadata_info = unitDefinations.unit_info
        self.__dssDolver = dssSolver
        self.Results = {}
        self.CurrentResults = {}
        self.pyLogger = logging.getLogger(LoggerTag)
        self.Buses = dssBuses
        self.ObjectsByElement = dssObjects
        self.ObjectsByClass = dssObjectsByClass
        self.SystemPaths = SystemPaths
        self.__dssCommand = dssCommand
        self.__Settings = Options
        self.__StartDay = Options['Start Day']
        self.__EndDay = Options['End Day']
        self.__DateTime = []
        self.__Frequency = []
        self.__SimulationMode = []

        self.__publications = {}
        self.__subscriptions = {}

        self.ExportFolder = os.path.join(self.SystemPaths['Export'], Options['Active Scenario'])
        pathlib.Path(self.ExportFolder).mkdir(parents=True, exist_ok=True)
        if self.__Settings['Export Mode'] == 'byElement':
            self.FileReader = pyER(os.path.join(SystemPaths['ExportLists'], 'ExportMode-byElement.toml'))
            self.ExportList = self.FileReader.pyControllers
            self.PublicationList = self.FileReader.publicationList
            self.CreateListByElement()
        elif self.__Settings['Export Mode'] == 'byClass':
            self.FileReader = pyER(os.path.join(SystemPaths['ExportLists'], 'ExportMode-byClass.toml'))
            self.ExportList = self.FileReader.pyControllers
            self.PublicationList = self.FileReader.publicationList
            self.CreateListByClass()
        if self.__Settings['Co-simulation Mode']:
            self.__createPyDSSfederate()
            self.__registerFederatePublications()
            self.__registerFederateSubscriptions()
            h.helicsFederateEnterExecutingMode(self.__PyDSSfederate)
            self.pyLogger.debug('Entered HELICS execution mode')
        return

    def __createPyDSSfederate(self):
        fedinfo = h.helicsCreateFederateInfo()
        h.helicsFederateInfoSetCoreName(fedinfo, self.__Settings['Federate name'])
        h.helicsFederateInfoSetCoreTypeFromString(fedinfo, self.__Settings['Core type'])
        h.helicsFederateInfoSetCoreInitString(fedinfo, "--federates=1")
        h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, self.__Settings['Time delta'])
        h.helicsFederateInfoSetIntegerProperty(fedinfo, h.helics_property_int_log_level,
                                                self.__Settings['Helics logging level'])

        h.helicsFederateInfoSetFlagOption(fedinfo, h.helics_flag_uninterruptible, True)
        self.__PyDSSfederate = h.helicsCreateValueFederate(self.__Settings['Federate name'], fedinfo)
        return

    def __registerFederateSubscriptions(self):
        self.FileReader = pySR(os.path.join(self.SystemPaths['ExportLists'], 'Helics-Subcriptions.xlsx'))
        self.__subscriptions = self.FileReader.SubscriptionDict

        for element, subscription in self.__subscriptions.items():
            assert element in self.ObjectsByElement, '"{}" listed in the subscription file not '.format(element) +\
                                                     "available in PyDSS's master object dictionary."
            if subscription["Subscribe"] == True:
                sub = h.helicsFederateRegisterSubscription(self.__PyDSSfederate, subscription["Subscription ID"],
                                                           subscription["Unit"])
                self.pyLogger.debug('PyDSS subscribing to "{}" of  with units "{}"'.format(
                    subscription["Subscription ID"],
                    subscription["Unit"])
                )
                subscription['Subscription'] = sub
            self.__subscriptions[element] = subscription
        return

    def updateSubscriptions(self):
        for element, subscriptionData in self.__subscriptions.items():
            if 'Subscription' in subscriptionData:
                if subscriptionData['Data type'].lower() == 'double':
                    value = h.helicsInputGetDouble(subscriptionData['Subscription'])
                elif subscriptionData['Data type'].lower() == 'vector':
                    value = h.helicsInputGetVector(subscriptionData['Subscription'])
                elif subscriptionData['Data type'].lower() == 'string':
                    value = h.helicsInputGetString(subscriptionData['Subscription'])
                elif subscriptionData['Data type'].lower() == 'boolean':
                    value = h.helicsInputGetBoolean(subscriptionData['Subscription'])
                elif subscriptionData['Data type'].lower() == 'integer':
                    value = h.helicsInputGetInteger(subscriptionData['Subscription'])
                dssElement = self.ObjectsByElement[element]
                dssElement.SetParameter(subscriptionData['Property'], value)
                self.pyLogger.debug('Value for "{}.{}" changed to "{}"'.format(
                    element,
                    subscriptionData['Property'],
                    value
                ))

        return

    def __registerFederatePublications(self):
        self.__publications = {}
        for object, property_dict in self.CurrentResults.items():
            objClass = None
            for Class in self.ObjectsByClass:
                if object in self.ObjectsByClass[Class]:
                    objClass = Class
                    break
            for property, type_dict in property_dict.items():
                if '{} {}'.format(objClass, property) in self.PublicationList:
                    for typeID, type in type_dict.items():
                        name = '{}.{}.{}'.format(object, property, typeID)

                        self.__publications[name] = h.helicsFederateRegisterGlobalTypePublication(
                            self.__PyDSSfederate,
                            name,
                            type['type'],
                            type['unit']
                        )

        return

    def __initCurrentResults(self, PptyName):
        data = {}
        if PptyName in Units:
            if isinstance(Units[PptyName], dict):
                for subset, unit in Units[PptyName].items():
                    data[subset] = {
                        'value': None,
                        'unit': Units[PptyName][subset],
                        'type': Types[PptyName]
                    }
            else:
                data['A'] = {
                    'value': None,
                    'unit': Units[PptyName],
                    'type': Types[PptyName]
                }
        else:
            data['A'] = {
                'value': None,
                'unit': 'NA',
                'type': 'double'
            }
        return data

    def CreateListByClass(self):
        for Class, Properties in enumerate(self.ExportList):
            if Class == 'Buses':
                self.Results[Class] = {}
                for PptyIndex, PptyName in enumerate(Properties):
                    if isinstance(PptyName, str):
                        self.Results[Class][PptyName] = {}
                        for BusName, BusObj in self.Buses.items():
                            if self.Buses[BusName].inVariableDict(PptyName):
                                self.Results[Class][PptyName][BusName] = []
                                if BusName not in self.CurrentResults:
                                    self.CurrentResults[BusName] = {}
                                self.CurrentResults[BusName][PptyName] = self.__initCurrentResults(PptyName)
            else:
                if Class in self.ObjectsByClass:
                    self.Results[Class] = {}
                    for PptyIndex, PptyName in enumerate(Properties):
                        if isinstance(PptyName, str):
                            self.Results[Class][PptyName] = {}
                            for ElementName, ElmObj in self.ObjectsByClass[Class].items():
                                if self.ObjectsByClass[Class][ElementName].IsValidAttribute(PptyName):
                                    self.Results[Class][PptyName][ElementName] = []
                                    if ElementName not in self.CurrentResults:
                                        self.CurrentResults[ElementName] = {}
                                    self.CurrentResults[ElementName][PptyName] = self.__initCurrentResults(PptyName)
        return

    def CreateListByElement(self):
        for Element, Properties in enumerate(self.ExportList):
            if Element in self.ObjectsByElement:
                self.Results[Element] = {}
                self.CurrentResults[Element] = {}
                for PptyIndex, PptyName in enumerate(Properties):
                    if isinstance(PptyName, str):
                        if self.ObjectsByElement[Element].IsValidAttribute(PptyName):
                            self.Results[Element][PptyName] = []
                            self.CurrentResults[Element][PptyName] = self.__initCurrentResults(PptyName)
            elif Element in self.Buses:
                self.Results[Element] = {}
                self.CurrentResults[Element] = {}
                for PptyIndex, PptyName in enumerate(Properties):
                    if isinstance(PptyName, str):
                        if self.Buses[Element].inVariableDict(PptyName):
                            self.Results[Element][PptyName] = []
                            self.CurrentResults[Element][PptyName] = self.__initCurrentResults(PptyName)
        return

    def __parse_current_values(self, Element, Property, Values):

        ans = self.CurrentResults[Element][Property]
        for filter, data in ans.items():
            if filter == 'A':
                ans[filter]['value'] = Values
            elif filter == 'E':
                ans[filter]['value'] = Values[0::2]
            elif filter == '0':
                ans[filter]['value'] = Values[1::2]
            if self.__Settings['Co-simulation Mode']:
                name = '{}.{}.{}'.format(Element, Property, filter)
                if isinstance(ans[filter]['value'], list) and name in self.__publications:
                    h.helicsPublicationPublishVector(self.__publications[name], ans[filter]['value'])
                elif isinstance(Values, float) and name in self.__publications:
                    h.helicsPublicationPublishDouble(self.__publications[name], ans[filter]['value'])
                elif isinstance(Values, str) and name in self.__publications:
                    h.helicsPublicationPublishString(self.__publications[name], ans[filter]['value'])
                elif isinstance(Values, bool) and name in self.__publications:
                    h.helicsPublicationPublishBoolean(self.__publications[name], ans[filter]['value'])
                elif isinstance(Values, int) and name in self.__publications:
                    h.helicsPublicationPublishInteger(self.__publications[name], ans[filter]['value'])

            self.CurrentResults[Element][Property] = ans
        return

    def UpdateResults(self):
        if self.__Settings['Co-simulation Mode']:
            r_seconds = self.__dssDolver.GetTotalSeconds()
            print('Time: ', r_seconds)
            c_seconds = 0
            while c_seconds < r_seconds:
                c_seconds = h.helicsFederateRequestTime(self.__PyDSSfederate, r_seconds)

        self.__DateTime.append(self.__dssDolver.GetDateTime())
        self.__Frequency.append(self.__dssDolver.getFrequency())
        self.__SimulationMode.append(self.__dssDolver.getMode())

        if self.__Settings['Export Mode'] == 'byElement':
            for Element in self.Results.keys():
                for Property in self.Results[Element].keys():
                    if '.' in Element:
                        value = self.ObjectsByElement[Element].GetValue(Property)
                        self.Results[Element][Property].append(value)
                        self.__parse_current_values(Element, Property, value)
                    else:
                        value = self.Buses[Element].GetVariable(Property)
                        self.Results[Element][Property].append(value)
                        self.__parse_current_values(Element, Property, value)
        elif self.__Settings['Export Mode'] == 'byClass':
            for Class in self.Results.keys():
                for Property in self.Results[Class].keys():
                    for Element in self.Results[Class][Property].keys():
                        if Class == 'Buses':
                            value = self.Buses[Element].GetVariable(Property)
                            self.Results[Class][Property][Element].append(value)
                            self.__parse_current_values(Element, Property, value)
                        else:
                            value = self.ObjectsByClass[Class][Element].GetValue(Property)
                            self.Results[Class][Property][Element].append(value)
                            self.__parse_current_values(Element, Property, value)
        return

    def ExportResults(self, fileprefix=''):
        if self.__Settings['Export Mode'] == 'byElement':
            self.__ExportResultsByElements(fileprefix)
        elif self.__Settings['Export Mode'] == 'byClass':
            self.__ExportResultsByClass(fileprefix)
        self.__ExportEventLog()

    def __ExportResultsByClass(self, fileprefix=''):
        for Class in self.Results.keys():
            for Property in self.Results[Class].keys():
                Class_ElementDatasets = []
                PptyLvlHeader = ''
                for Element in self.Results[Class][Property].keys():
                    ElmLvlHeader = ''
                    if isinstance(self.Results[Class][Property][Element][0], list):
                        Data = np.array(self.Results[Class][Property][Element])
                        for i in range(len(self.Results[Class][Property][Element][0])):
                            if Property in self.metadata_info:
                                if i % 2 == 0 and 'E' in self.metadata_info[Property]:
                                    ElmLvlHeader += '{} ph:{} [{}],'.format(Element,  math.floor(i / 2) + 1,
                                                                           self.metadata_info[Property]['E'])
                                elif i % 2 == 1 and 'O' in self.metadata_info[Property]:
                                    ElmLvlHeader += '{} ph:{} [{}],'.format(Element, math.floor(i / 2) + 1,
                                                                           self.metadata_info[Property]['O'])
                                else:
                                    ElmLvlHeader += '{}-{} [{}],'.format(Element, i, self.metadata_info[Property])
                            else:
                                ElmLvlHeader += Element + '-' + str(i) + ','
                    else:
                        Data = np.transpose(np.array([self.Results[Class][Property][Element]]))
                        if Property in self.metadata_info:
                            ElmLvlHeader = '{} [{}],'.format(Element, self.metadata_info[Property])
                        else:
                            ElmLvlHeader = Element + ','
                    if self.__Settings['Export Style'] == 'Separate files':
                        fname = '-'.join([Class, Property, Element, str(self.__StartDay), str(self.__EndDay) ,fileprefix]) + '.csv'
                        columns = [x for x in ElmLvlHeader.split(',') if x != '']
                        tuples = list(zip(*[self.__DateTime, self.__Frequency, self.__SimulationMode]))
                        index = pd.MultiIndex.from_tuples(tuples, names=['timestamp', 'frequency', 'Simulation mode'])
                        df = pd.DataFrame(Data, index=index, columns=columns)
                        df.to_csv(os.path.join(self.ExportFolder, fname))
                        self.pyLogger.info(Class + '-' + Property  + '-' + Element + ".csv exported to " + self.ExportFolder)
                    elif self.__Settings['Export Style'] == 'Single file':
                        Class_ElementDatasets.append(Data)
                    PptyLvlHeader += ElmLvlHeader
                if self.__Settings['Export Style'] == 'Single file':
                    assert Class_ElementDatasets
                    Dataset = Class_ElementDatasets[0]
                    if len(Class_ElementDatasets) > 1:
                        for D in Class_ElementDatasets[1:]:
                            Dataset = np.append(Dataset, D, axis=1)
                    columns = [x for x in PptyLvlHeader.split(',') if x != '']
                    tuples = list(zip(*[self.__DateTime, self.__Frequency, self.__SimulationMode]))
                    index = pd.MultiIndex.from_tuples(tuples, names=['timestamp', 'frequency', 'Simulation mode'])
                    df = pd.DataFrame(Dataset, index=index, columns=columns)
                    fname = '-'.join([Class, Property, str(self.__StartDay), str(self.__EndDay), fileprefix]) + '.csv'
                    df.to_csv(os.path.join(self.ExportFolder, fname))
                    self.pyLogger.info(Class + '-' + Property + ".csv exported to " + self.ExportFolder)
        return

    def __ExportResultsByElements(self, fileprefix=''):
        for Element in self.Results.keys():
            ElementDatasets = []
            AllHeader = ''

            for Property in self.Results[Element].keys():
                Header = ''

                if isinstance(self.Results[Element][Property][0], list):
                    Data = np.array(self.Results[Element][Property])
                    for i in range(len(self.Results[Element][Property][0])):
                        if Property in self.metadata_info:
                            if i % 2 == 0 and 'E' in self.metadata_info[Property]:
                                Header += '{} ph:{} [{}],'.format(Property, math.floor(i / 2) + 1,
                                                                  self.metadata_info[Property]['E'])
                            elif i % 2 == 1 and 'O' in self.metadata_info[Property]:
                                Header += '{} ph:{} [{}],'.format(Property, math.floor(i / 2) + 1,
                                                                  self.metadata_info[Property]['O'])
                            else:
                                Header += '{}-{} [{}],'.format(Property, i, self.metadata_info[Property])
                        else:
                            Header += Property + '-' + str(i) + ','
                else:
                    Data = np.transpose(np.array([self.Results[Element][Property]]))
                    Header = Property + ','

                if self.__Settings['Export Style'] == 'Separate files':
                    fname = '-'.join([Element, Property, str(self.__StartDay), str(self.__EndDay), fileprefix]) + '.csv'
                    columns = [x for x in Header.split(',') if x != '']
                    tuples = list(zip(*[self.__DateTime, self.__Frequency, self.__SimulationMode]))
                    index = pd.MultiIndex.from_tuples(tuples, names=['timestamp', 'frequency', 'Simulation mode'])
                    df = pd.DataFrame(Data, index=index, columns=columns)
                    df.to_csv(os.path.join(self.ExportFolder, fname))
                    self.pyLogger.info(Element + '-' + Property + ".csv exported to " + self.ExportFolder)
                elif self.__Settings['Export Style'] == 'Single file':
                    ElementDatasets.append(Data)
                AllHeader += Header
            if self.__Settings['Export Style'] == 'Single file':
                Dataset = ElementDatasets[0]
                if len(ElementDatasets) > 0:
                    for D in ElementDatasets[1:]:
                        Dataset = np.append(Dataset, D, axis=1)
                fname = '-'.join([Element, str(self.__StartDay), str(self.__EndDay), fileprefix]) + '.csv'
                columns = [x for x in AllHeader.split(',') if x != '']
                tuples = list(zip(*[self.__DateTime, self.__Frequency, self.__SimulationMode]))
                index = pd.MultiIndex.from_tuples(tuples, names=['timestamp', 'frequency', 'Simulation mode'])
                df = pd.DataFrame(Dataset, index=index, columns=columns)
                df.to_csv(os.path.join(self.ExportFolder, fname))
                self.pyLogger.info(Element + ".csv exported to " + self.ExportFolder)
        return

    def __ExportEventLog(self):
        event_log = "event_log.csv"
        cmd = "Export EventLog {}".format(event_log)
        out = self.__dssCommand(cmd)
        self.pyLogger.info("Exported OpenDSS event log to %s", out)
        file_path = os.path.join(self.ExportFolder, event_log)
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(event_log, self.ExportFolder)

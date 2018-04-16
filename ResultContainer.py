from pyContrReader import pyContrReader as PCR
import numpy as np
import pathlib
import logging
import os
class ResultContainer:
    def __init__(self, ResultSettings, SimulationSettings, SystemPaths, dssObjects, dssObjectsByClass, dssBuses):
        LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
        self.Results = {}
        self.FileNumber = None
        self.pyLogger = logging.getLogger(LoggerTag)
        self.Buses = dssBuses
        self.ObjectsByElement = dssObjects
        self.ObjectsByClass = dssObjectsByClass
        self.SystemPaths = SystemPaths
        self.__Settings = ResultSettings
        self.__StartDay = SimulationSettings['Start Day']
        self.__EndDay = SimulationSettings['End Day']

        self.FileReader = PCR(SystemPaths['ExportLists'])

        self.ExportFolder = os.path.join(self.SystemPaths['Export'], SimulationSettings['Active Project'],
                                         SimulationSettings['Active Scenario'])

        pathlib.Path(self.ExportFolder).mkdir(parents=True, exist_ok=True)

        if self.__Settings['Export Mode'] == 'byElement':
            self.ExportList = self.FileReader.pyControllers['ExportMode-byElement']
            self.CreateListByElement()
        elif self.__Settings['Export Mode'] == 'byClass':
            self.ExportList = self.FileReader.pyControllers['ExportMode-byClass']
            self.CreateListByClass()
        return

    def CreateListByClass(self):
        self.Results = {}
        for Class , Properties in self.ExportList.items():
            if Class == 'Buses':
                self.Results[Class] = {}
                for PptyIndex, PptyName in Properties.items():
                    if isinstance(PptyName, str):
                        self.Results[Class][PptyName] = {}
                        for BusName, BusObj in self.Buses.items():
                            if self.Buses[BusName].inVariableDict(PptyName):
                                self.Results[Class][PptyName][BusName] = []
            else:
                if Class in self.ObjectsByClass:
                    self.Results[Class] = {}
                    for PptyIndex, PptyName in Properties.items():
                        if isinstance(PptyName, str):
                            self.Results[Class][PptyName] = {}
                            for ElementName, ElmObj in self.ObjectsByClass[Class].items():
                                if self.ObjectsByClass[Class][ElementName].IsValidAttribute(PptyName):
                                    self.Results[Class][PptyName][ElementName] = []
        return

    def CreateListByElement(self):
        self.Results = {}
        for Element, Properties in self.ExportList.items():
            if Element in self.ObjectsByElement:
                self.Results[Element] = {}
                for PptyIndex, PptyName in Properties.items():
                    if isinstance(PptyName, str):
                        if self.ObjectsByElement[Element].IsValidAttribute(PptyName):
                            self.Results[Element][PptyName] = []
            elif Element in self.Buses:
                self.Results[Element] = {}
                for PptyIndex, PptyName in Properties.items():
                    if isinstance(PptyName, str):
                        if self.Buses[Element].inVariableDict(PptyName):
                            self.Results[Element][PptyName] = []
        return

    def UpdateResults(self):
        if self.__Settings['Export Mode'] == 'byElement':
            for Element in self.Results.keys():
                for Property in self.Results[Element].keys():
                    if '.' in Element:
                        self.Results[Element][Property].append(self.ObjectsByElement[Element].GetValue(Property))
                    else:
                        self.Results[Element][Property].append(self.Buses[Element].GetVariable(Property))
        elif self.__Settings['Export Mode'] == 'byClass':
            for Class in self.Results.keys():
                for Property in self.Results[Class].keys():
                    for Element in self.Results[Class][Property].keys():
                        if Class == 'Buses':
                            self.Results[Class][Property][Element].append(self.Buses[Element].GetVariable(Property))
                        else:
                            self.Results[Class][Property][Element].append(
                                self.ObjectsByClass[Class][Element].GetValue(Property)
                            )
        return

    def ClearResults(self):
        if self.__Settings['Export Mode'] == 'byElement':
            self.CreateListByElement()
        elif self.__Settings['Export Mode'] == 'byClass':
            self.CreateListByClass()

    def ExportResults(self, RunNumber = None):
        if self.__Settings['Export Mode'] == 'byElement':
            self.__ExportResultsByElements(RunNumber)
        elif self.__Settings['Export Mode'] == 'byClass':
            self.__ExportResultsByClass(RunNumber)

    def __ExportResultsByClass(self, RunNumber = None):
        for Class in self.Results.keys():
            for Property in self.Results[Class].keys():
                Class_ElementDatasets = []
                PptyLvlHeader = ''
                for Element in self.Results[Class][Property].keys():
                    ElmLvlHeader = ''
                    if isinstance(self.Results[Class][Property][Element][0], list):
                        Data = np.array(self.Results[Class][Property][Element])
                        for i in range(len(self.Results[Class][Property][Element][0])):
                            ElmLvlHeader += Element + '-' + str(i) + ','
                    else:
                        Data = np.transpose(np.array([self.Results[Class][Property][Element]]))
                        ElmLvlHeader = Element + ','

                    if self.__Settings['Export Style'] == 'Seperate files':
                        if RunNumber:
                            np.savetxt(self.ExportFolder + '\\' + Class + '_' + Property + '-' + Element + '-' +
                                       str(self.__StartDay) + '-' + str(self.__EndDay) + '-' + str(RunNumber) +
                                       ".csv", Data, delimiter=',', header=ElmLvlHeader, comments='', fmt='%f')
                        else:
                            np.savetxt(self.ExportFolder + '\\' + Class + '_' +  Property + '-' + Element + '-' +
                                        str(self.__StartDay) + '-' + str(self.__EndDay)+ ".csv", Data,
                                        delimiter=',', header=ElmLvlHeader, comments='', fmt='%f')
                        self.pyLogger.info(Class + '-' + Property  + '-' + Element + ".csv exported to " + self.ExportFolder)
                    elif self.__Settings['Export Style'] == 'Single file':
                        Class_ElementDatasets.append(Data)
                    PptyLvlHeader += ElmLvlHeader
                if self.__Settings['Export Style'] == 'Single file':
                    Dataset = Class_ElementDatasets[0]
                    if len(Class_ElementDatasets) > 0:
                        for D in Class_ElementDatasets[1:]:
                            Dataset = np.append(Dataset, D, axis=1)
                    if RunNumber:
                        np.savetxt(self.ExportFolder + '\\' + Class + '-' + Property + '-' + str(self.__StartDay) +
                                   '-' + str(self.__EndDay) + '-' + str(RunNumber) + ".csv", Dataset,
                                   delimiter=',', header=PptyLvlHeader, comments='',fmt='%f')
                    else:
                        np.savetxt(self.ExportFolder + '\\' + Class +'-' + Property + '-' + str(self.__StartDay) + '-' +
                                   str(self.__EndDay)+ ".csv", Dataset, delimiter=',', header=PptyLvlHeader, comments='',
                                   fmt='%f')
                    self.pyLogger.info(Class + '-' + Property + ".csv exported to " + self.ExportFolder)
        return


    def __ExportResultsByElements(self, RunNumber = None):
        for Element in self.Results.keys():
            ElementDatasets = []
            AllHeader = ''

            for Property in self.Results[Element].keys():
                Header = ''

                if isinstance(self.Results[Element][Property][0], list):
                    Data = np.array(self.Results[Element][Property])
                    for i in range(len(self.Results[Element][Property][0])):
                        Header += Property + '-' + str(i) + ','
                else:
                    Data = np.transpose(np.array([self.Results[Element][Property]]))
                    Header = Property + ','

                if self.__Settings['Export Style'] == 'Seperate files':
                    if RunNumber:
                        np.savetxt(self.ExportFolder + '\\' + Element + '-' + Property + '-' + str(self.__StartDay) +
                                   '-' + str(self.__EndDay) + '- ' + str(RunNumber) + ".csv", Data, delimiter=',',
                                   header=Header, comments='', fmt='%f')
                    else:
                        np.savetxt(self.ExportFolder + '\\' + Element + '-' + Property + '-' + str(self.__StartDay) +
                                   '-' + str(self.__EndDay) + ".csv", Data, delimiter=',', header=Header, comments='',
                                   fmt='%f')
                    self.pyLogger.info(Element + '-' + Property + ".csv exported to " + self.ExportFolder)
                elif self.__Settings['Export Style'] == 'Single file':
                    ElementDatasets.append(Data)
                AllHeader += Header
            if self.__Settings['Export Style'] == 'Single file':
                Dataset = ElementDatasets[0]
                if len(ElementDatasets) > 0:
                    for D in ElementDatasets[1:]:
                        Dataset = np.append(Dataset, D, axis=1)
                if RunNumber:
                    np.savetxt(self.ExportFolder + '\\' + Element + '-' + str(self.__StartDay) + '-' +
                               str(self.__EndDay) + '- ' + str(RunNumber) + ".csv", Dataset, delimiter=',',
                               header=AllHeader, comments='', fmt='%f')
                else:
                    np.savetxt(self.ExportFolder + '\\' + Element + '-' + str(self.__StartDay) + '-' +
                               str(self.__EndDay)+ ".csv", Dataset, delimiter=',', header=AllHeader, comments='',
                               fmt='%f')
                self.pyLogger.info(Element + ".csv exported to " + self.ExportFolder)
        return
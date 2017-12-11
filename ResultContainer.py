from pyContrReader import pyContrReader as PCR
import pandas as pd
import numpy as np
class ResultContainer:
    Results = {}
    def __init__(self, ResultSettings, SystemPaths, dssObjects, dssObjectsByClass):

        self.ObjectsByElement = dssObjects
        self.ObjectsByClass = dssObjectsByClass
        self.SystemPaths = SystemPaths
        self.__Settings = ResultSettings

        self.FileReader = PCR(SystemPaths['ExportLists'])

        if self.__Settings['Export Mode'] == 'byElement':
            self.ExportList = self.FileReader.pyControllers['ExportMode-byElement']
            self.CreateListByElement()
        elif self.__Settings['Export Mode'] == 'byClass':
            self.ExportList = self.FileReader.pyControllers['ExportMode-byClass']
            self.CreateListByClass()

    def CreateListByClass(self):
        self.Results = {}
        for Class , Properties in self.ExportList.items():
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
        return

    def UpdateResults(self):
        if self.__Settings['Export Mode'] == 'byElement':
            for Element in self.Results.keys():
                for Property in self.Results[Element].keys():
                    self.Results[Element][Property].append(self.ObjectsByElement[Element].GetValue(Property))
        elif self.__Settings['Export Mode'] == 'byClass':
            for Class in self.Results.keys():
                for Property in self.Results[Class].keys():
                    for Element in self.Results[Class][Property].keys():
                        self.Results[Class][Property][Element].append(self.ObjectsByClass[Class][Element].GetValue(Property))
        return


    def ExportResults(self):
        if self.__Settings['Export Mode'] == 'byElement':
            self.__ExportResultsByElements()
        elif self.__Settings['Export Mode'] == 'byClass':
            self.__ExportResultsByClass()


    def __ExportResultsByClass(self):
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
                        np.savetxt(self.SystemPaths['Export'] + '\\' + Class + '_' +  Property +
                                   '-' + Element + ".csv", Data,
                                   delimiter=',', header=ElmLvlHeader, comments='', fmt='%f')
                        print(Class + '-' + Property  + '-' + Element + ".csv exported to " + self.SystemPaths['Export'])
                    elif self.__Settings['Export Style'] == 'Single file':
                        Class_ElementDatasets.append(Data)
                    PptyLvlHeader += ElmLvlHeader
                if self.__Settings['Export Style'] == 'Single file':
                    Dataset = Class_ElementDatasets[0]
                    if len(Class_ElementDatasets) > 0:
                        for D in Class_ElementDatasets[1:]:
                            Dataset = np.append(Dataset, D, axis=1)
                    np.savetxt(self.SystemPaths['Export'] + '\\' + Class +'-' + Property+ ".csv", Dataset,
                               delimiter=',', header=PptyLvlHeader, comments='', fmt='%f')
                    print(Class + '-' + Property + ".csv exported to " + self.SystemPaths['Export'])
        return


    def __ExportResultsByElements(self):
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
                    np.savetxt(self.SystemPaths['Export'] + '\\' + Element + '-' + Property + ".csv", Data,
                               delimiter=',', header=Header, comments='', fmt='%f')
                    print(Element + '-' + Property + ".csv exported to " + self.SystemPaths['Export'])
                elif self.__Settings['Export Style'] == 'Single file':
                    ElementDatasets.append(Data)
                AllHeader += Header
            if self.__Settings['Export Style'] == 'Single file':
                Dataset = ElementDatasets[0]
                if len(ElementDatasets) > 0:
                    for D in ElementDatasets[1:]:
                        Dataset = np.append(Dataset, D, axis=1)
                np.savetxt(self.SystemPaths['Export'] + '\\' + Element + ".csv", Dataset,
                           delimiter=',', header=AllHeader, comments='', fmt='%f')
                print(Element + ".csv exported to " + self.SystemPaths['Export'])
        return
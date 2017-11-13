from opendssdirect.utils import run_command
from dssElement import dssElement
import opendssdirect as dss
from dssBus import dssBus
import pandas as pd
import SolveMode
import time
import sys
import os

sys.path.insert(0, './pyControllers')
sys.path.insert(0, './pyPlots')
import pyController
import pyPlots

class OpenDSS:
    __TempResultList = []

    print ('An instance of OpenDSS version ' + dss.__version__ + ' has ben created.')
    __dssInstance = dss
    __dssBuses = {}
    __dssObjects = {}
    __dssObjectsByClass = {}
    __DelFlag = 0
    __pyPlotObjects = {}
    def __init__(self , SimType = 'Daily', rootPath = os.getcwd(), dssMainFile = 'IEEE13Nodeckt.dss',
                 ExportList = None, ControllerList = None, PlotList = None):

        self.__ExportList = ExportList
        self.__PlotDict = PlotList
        self.__dssPath = {
            'root': rootPath,
            'Import': rootPath + '\\Import',
            'Export': rootPath + '\\Export',
            'dssFiles': rootPath + '\\dssFiles',
            'Profiles': {
                'PV': rootPath + '\\Profiles\\PV',
                'WT': rootPath + '\\Profiles\\WT',
                'GN': rootPath + '\\Profiles\\GN',
                'LD': rootPath + '\\Profiles\\LD'
            }
        }
        self.__dssFilePath = self.__dssPath['dssFiles'] + '\\' + dssMainFile

        self.__dssInstance.Basic.ClearAll()
        run_command('Clear')
        run_command('compile ' + self.__dssFilePath)

        self.__dssCircuit = dss.Circuit
        self.__dssElement = dss.Element
        self.__dssBus = dss.Bus
        self.__dssClass = dss.ActiveClass
        self.__dssCommand = run_command
        self.__dssSolution = dss.Solution
        self.__dssSolver = SolveMode.GetSolver(SimType, self.__dssInstance)

        self.__ModifyNetwork()
        self.__UpdateDictionary()
        self.__CreateBusObjects()

        if self.__ExportList:
            self.__PrepareExportList(self.__ExportList)
        if ControllerList is not None and isinstance(ControllerList, dict):
            self.__CreateControllers(ControllerList)
        #self.__CreatePlots(PlotList)
        return

    def __ModifyNetwork(self):
        from NetworkModifier import Modifier
        self.__Modifier = Modifier(dss, run_command)
        self.__Modifier.Add_Elements('PVSystem', {'bus' : ['671.1','671.2','671.3','645.2','675.1',
                                                           '675.2','675.3','670.1','670.2','670.3'],
                                                  'kVA' : ['500','500','500','200','50',
                                                           '200','300','100','75','125']})

        self.__Modifier.Add_Elements('Storage', {'bus' : ['671'], 'kWRated' : ['500'], 'kWhRated'  : ['2000']},
                                     True, self.__dssObjects)

        return

    def __CreateControllers(self,ControllerDict):
        self.__pyControls = {}
        for ControllerType, ElmentsDict in ControllerDict.items():
            for ElmName, SettingsDict in ElmentsDict.items():
                 Controller = pyController.Create(ElmName, ControllerType, SettingsDict, self.__dssObjects,
                                                  self.__dssInstance, self.__dssSolver)
                 if Controller != -1:
                    self.__pyControls['Controller.' + ElmName] = Controller
                    print('Created pyController -> Controller.' + ElmName)
        return


    def __CreatePlots(self, PlotsDict):
        __pyPlotObjects= {}
        for PlotType, PlotSettings in PlotsDict.items():
            if PlotSettings == None:
                self.__pyPlotObjects[PlotType] = pyPlots.Create(PlotType, None,
                                                self.__dssBuses, self.__dssObjectsByClass)
            else:
                self.__pyPlotObjects[PlotType+str(PlotSettings)] = pyPlots.Create(PlotType, PlotSettings,
                                                                self.__dssBuses, self.__dssObjectsByClass)
        return

    def __UpdateControllers(self, Time, UpdateResults):

        NewError = 0
        for Key, Controller in self.__pyControls.items():
            NewError += Controller.Update(Time, UpdateResults)

        if abs(NewError) < 1e-4:
            return True

        return False

    def __CreateBusObjects(self):
        BusNames = self.__dssCircuit.AllBusNames()
        for BusName in BusNames:
            self.__dssCircuit.SetActiveBus(BusName)
            self.__dssBuses[BusName] = dssBus(self.__dssInstance)
        return

    def __UpdateDictionary(self):
        InvalidSelection = ['Settings', 'ActiveClass', 'dss', 'utils', 'PDElements', 'XYCurves', 'Bus', 'Properties']
        self.__dssObjectsByClass={'LoadShape' : self.__GetRelaventObjectDict('LoadShape')}
        for key in dss.__dict__.keys():
            if key[-1] == 's' and (key not in InvalidSelection):
                self.__dssObjectsByClass[key] = self.__GetRelaventObjectDict(key)

        for ClassType in self.__dssObjectsByClass.keys():
            for ElmName in self.__dssObjectsByClass[ClassType].keys():
                self.__dssObjects[ElmName] = self.__dssObjectsByClass[ClassType][ElmName]
        return

    def __GetRelaventObjectDict(self, key):
        ObjectList = {}
        ElmCollection = getattr(dss, key)
        Elem =  ElmCollection.First()
        while Elem:
            ObjectList[self.__dssInstance.Element.Name()] =  dssElement(self.__dssInstance)
            Elem = ElmCollection.Next()
        return ObjectList

    def __PrepareExportList(self,ExportDictionary, ElmWise = False, FileName = None):
        HeaderClass = []
        HeaderName = []
        HeaderPpty = []
        HeaderPhase = []

        if ElmWise == False:
            for ClassName, VariableNames in ExportDictionary.items():
                for VariableName in VariableNames:
                    if ClassName in self.__dssObjectsByClass and self.__dssObjectsByClass[ClassName]:
                        for ElmName in self.__dssObjectsByClass[ClassName].keys():
                            if self.__dssObjectsByClass[ClassName][ElmName].inVariableDict(VariableName):
                                DataLength, DataType = self.__dssObjectsByClass[ClassName][ElmName].DataLength(VariableName)
                                if DataType == 'List':
                                    for i in range(DataLength):
                                        HeaderClass.append(ClassName)
                                        HeaderName.append(ElmName)
                                        HeaderPpty.append(VariableName)
                                        HeaderPhase.append(i)
                                else:
                                    HeaderClass.append(ClassName)
                                    HeaderName.append(ElmName)
                                    HeaderPpty.append(VariableName)
                                    HeaderPhase.append('-N/A-')

        self.__ExportResults = pd.DataFrame(columns=HeaderClass)
        self.__ExportResults.columns = pd.MultiIndex.from_tuples(list(zip(self.__ExportResults.columns, HeaderName, HeaderPpty, HeaderPhase)), sortorder=None)
        return

    def RunSimulation(self, Steps, ControllerMaxItrs = 25):
        startTime = time.time()
        for i in range(Steps):
            print ('Time - ', i)
            for j in range(ControllerMaxItrs):

                hasConverged = self.__UpdateControllers(i, UpdateResults = False)

                if hasConverged or j == ControllerMaxItrs - 1:
                    self.__UpdateControllers(i, UpdateResults = True)
                    if not hasConverged:
                        print('No convergance @ ', i)
                    break
                elif not hasConverged:
                    self.__dssSolver.reSolve()
            self.__dssSolver.IncStep(i)
            if self.__ExportList:
                self.__UpdateResults()

        import matplotlib.pyplot as plt
        plt.show()

        if self.__ExportList:
            self.__ExportResults = pd.DataFrame(self.__TempResultList, columns = self.__ExportResults.columns)
        print ('Simulation completed in ' + str(time.time() - startTime) + ' seconds')
        print ('End of simulation')

    def __UpdateResults(self):
        ClassNames = list(self.__ExportResults.columns.get_level_values(0))
        ElemNames = list(self.__ExportResults.columns.get_level_values(1))
        PptyNames = list(self.__ExportResults.columns.get_level_values(2))
        ZippedHeader = set(zip(ClassNames,ElemNames, PptyNames))
        Results = []
        for ClassName,ElemName, PptyName in ZippedHeader:
            ReturnedData = self.__dssObjectsByClass[ClassName][ElemName].GetVariable(PptyName)
            if isinstance(ReturnedData, list):
                Results.extend(ReturnedData)
            else:
                Results.extend([ReturnedData])
        self.__TempResultList.append(Results)
        return

    def DeleteInstance(self):
        self.__DelFlag = 1
        self.__del__()
        return

    def __del__(self):
        if self.__DelFlag == 1:
            print ('An intstance of OpenDSS (' + str(self) +') has been deleted.')
        else:
            print ('An intstance of OpenDSS (' + str(self) + ') crashed.')
        return

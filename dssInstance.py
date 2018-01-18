from ResultContainer import ResultContainer  as RC
from pyContrReader import pyContrReader as pcr
from pyPlotReader import pyPlotReader as ppr
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
import pyLogger
import logging

class OpenDSS:
    __TempResultList = []
    __dssInstance = dss
    __dssBuses = {}
    __dssObjects = {}
    __dssObjectsByClass = {}
    __DelFlag = 0
    __pyPlotObjects = {}

    def __init__(self, rootPath = os.getcwd(), ResultOptions = None, PlotOptions = pyPlots.defalultPO ,
                 SimulationSettings =  None, LoggerOptions = None):
        LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
        self.__Logger = pyLogger.getLogger(LoggerTag, LoggerOptions=LoggerOptions)
        self.__Logger.info('An instance of OpenDSS version ' + dss.__version__ + ' has ben created.')

        self.__dssPath = {
            'root': rootPath,
            'Import': rootPath + '\\ProjectFiles\\' + SimulationSettings['Active Project'] + '\\PyDSS Settings',
            'Export': rootPath + '\\Export',
            'dssFiles': rootPath + '\\ProjectFiles\\' + SimulationSettings['Active Project'] + '\\DSSfiles',
        }

        self.__dssPath['pyPlots'] = self.__dssPath['Import'] + '\\' + SimulationSettings['Active Scenario'] + '\\pyPlotList'
        self.__dssPath['ExportLists'] = self.__dssPath['Import']+ '\\'  + SimulationSettings['Active Scenario'] + '\\ExportLists'
        self.__dssPath['pyControllers'] = self.__dssPath['Import']+ '\\'  + SimulationSettings['Active Scenario'] + '\\pyControllerList'

        self.__SimulationOptions = SimulationSettings
        self.__ResultOptions = ResultOptions
        self.__PlotOptions = PlotOptions
        self.__dssFilePath = self.__dssPath['dssFiles'] + '\\' + SimulationSettings['DSS File']

        self.__dssInstance.Basic.ClearAll()
        self.__dssInstance.utils.run_command('Log=NO')
        run_command('Clear')
        run_command('compile ' + self.__dssFilePath)

        self.__dssCircuit = dss.Circuit
        self.__dssElement = dss.Element
        self.__dssBus = dss.Bus
        self.__dssClass = dss.ActiveClass
        self.__dssCommand = run_command
        self.__dssSolution = dss.Solution
        self.__dssSolver = SolveMode.GetSolver(SimulationSettings=SimulationSettings, dssInstance=self.__dssInstance)

        self.__ModifyNetwork()
        self.__UpdateDictionary()
        self.__CreateBusObjects()
        self.__dssSolver.reSolve()

        if self.__ResultOptions and self.__ResultOptions['Log Results']:
            self.ResultContainer = RC(ResultOptions, SimulationSettings, self.__dssPath,
                                      self.__dssObjects, self.__dssObjectsByClass)

        pyCtrlReader = pcr(self.__dssPath['pyControllers'])
        ControllerList = pyCtrlReader.pyControllers
        if ControllerList is not None:
            self.__CreateControllers(ControllerList)

        pyPlotReader = ppr(self.__dssPath['pyPlots'])
        PlotList = pyPlotReader.pyPlots
        if PlotList is not None:
            self.__CreatePlots(PlotList)
        return

    def __ModifyNetwork(self):
        from NetworkModifier import Modifier
        self.__Modifier = Modifier(dss, run_command, self.__SimulationOptions)

        self.__Modifier.Add_Elements('Storage', {'bus' : ['storagebus'], 'kWRated' : ['2000'], 'kWhRated'  : ['2000']},
                                     True, self.__dssObjects)
        #self.__Modifier.Edit_Elements('regcontrol', 'enabled' ,'False')
        #self.__Modifier.Edit_Elements('Load', 'enabled', 'False')
        return

    def __CreateControllers(self,ControllerDict):
        self.__pyControls = {}

        for ControllerType, ElmentsDict in ControllerDict.items():
            for ElmName, SettingsDict in ElmentsDict.items():
                 Controller = pyController.Create(ElmName, ControllerType, SettingsDict, self.__dssObjects,
                                                  self.__dssInstance, self.__dssSolver)
                 if Controller != -1:
                    self.__pyControls['Controller.' + ElmName] = Controller
                    self.__Logger.info('Created pyController -> Controller.' + ElmName)
        return

    def __CreatePlots(self, PlotsDict):
        for PlotType, PlotNames in PlotsDict.items():
            newPlotNames = list(PlotNames)
            PlotType1= ['Network layout', 'GIS overlay']
            PlotType2 = ['Sag plot', 'GIS Histogram']
            PlotType3 = ['XY plot', 'Time series']
            for Name in newPlotNames:
                PlotSettings = PlotNames[Name]
                PlotSettings['FileName'] = Name
                if PlotType in PlotType1 and self.__PlotOptions[PlotType]:
                    self.__pyPlotObjects[PlotType] = pyPlots.Create(PlotType, PlotSettings,self.__dssBuses,
                                                                    self.__dssObjectsByClass,self.__dssCircuit)
                    self.__Logger.info('Created pyPlot -> ' + PlotType)
                elif PlotType in PlotType2 and self.__PlotOptions[PlotType]:
                    self.__pyPlotObjects[PlotType + Name] = pyPlots.Create(PlotType, PlotSettings,self.__dssBuses,
                                                                           self.__dssObjectsByClass, self.__dssCircuit)
                    self.__Logger.info('Created pyPlot -> ' + PlotType)
                elif PlotType in PlotType3  and self.__PlotOptions[PlotType]:
                    self.__pyPlotObjects[PlotType+Name] = pyPlots.Create(PlotType, PlotSettings,self.__dssBuses,
                                                                         self.__dssObjects, self.__dssCircuit)
                    self.__Logger.info('Created pyPlot -> ' + PlotType)
        return

    def __UpdateControllers_Q(self, Time, UpdateResults):
        NewError = 0
        for Key, Controller in self.__pyControls.items():
            NewError += Controller.Update_Q(Time, UpdateResults)

        if abs(NewError) < 0.01:
            return True
        return False

    def __UpdateControllers_P(self, Time, UpdateResults):
        NewError = 0
        for Key, Controller in self.__pyControls.items():
            NewError += Controller.Update_P(Time, UpdateResults)

        if abs(NewError) < 0.01:
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

    def RunSimulation(self):
        startTime = time.time()
        TotalDays = self.__SimulationOptions['End Day'] - self.__SimulationOptions['Start Day']
        Steps = int(TotalDays * 24 * 60 / self.__SimulationOptions['Step resolution (min)'])
        self.__Logger.info('Running simulation for ' + str(Steps) + ' time steps')
        for i in range(Steps):
            for j in range(self.__SimulationOptions['Max Control Iterations']):
                has_Q_Converged = self.__UpdateControllers_Q(i, UpdateResults = False)
                if has_Q_Converged or j == self.__SimulationOptions['Max Control Iterations'] - 1:
                    if not has_Q_Converged:
                        self.__Logger.warning('No convergance @ ', i)
                    break
                elif not has_Q_Converged:
                    self.__dssSolver.reSolve()
            self.__dssSolver.reSolve()
            for j in range(self.__SimulationOptions['Max Control Iterations']):
                has_P_Converged = self.__UpdateControllers_P(i, UpdateResults = False)
                if has_P_Converged or j == self.__SimulationOptions['Max Control Iterations'] - 1:
                    if not has_P_Converged:
                        self.__Logger.warning('No convergance @ ', i)
                    break
                elif not has_P_Converged:
                    self.__dssSolver.reSolve()
            self.__dssSolver.reSolve()
            self.__UpdatePlots()
            self.__dssSolver.IncStep()

            if self.__ResultOptions and self.__ResultOptions['Log Results']:
                self.ResultContainer.UpdateResults()

        if self.__ResultOptions and self.__ResultOptions['Log Results']:
            self.ResultContainer.ExportResults()

        self.__Logger.info('Simulation completed in ' + str(time.time() - startTime) + ' seconds')
        self.__Logger.info('End of simulation')

    def __UpdatePlots(self):
        for Plot in self.__pyPlotObjects:
            self.__pyPlotObjects[Plot].UpdatePlot()
        return

    def DeleteInstance(self):
        self.__DelFlag = 1
        self.__del__()
        return

    def __del__(self):
        if self.__DelFlag == 1:
            self.__Logger.info('An intstance of OpenDSS (' + str(self) +') has been deleted.')
        else:
            self.__Logger.error('An intstance of OpenDSS (' + str(self) + ') crashed.')
        return
#
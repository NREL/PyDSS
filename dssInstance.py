from ResultContainer import ResultContainer  as RC
from pyContrReader import pyContrReader as pcr
from pyPlotReader import pyPlotReader as ppr
from opendssdirect.utils import run_command
from dssElement import dssElement
from dssCircuit import dssCircuit
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

CONTROLLER_PRIORITIES = 3

class OpenDSS:
    __TempResultList = []
    __dssInstance = dss
    __dssBuses = {}
    __dssObjects = {}
    __dssObjectsByClass = {}
    __DelFlag = 0
    __pyPlotObjects = {}
    BokehSessionID = None
    def __init__(self, rootPath = os.getcwd(), ResultOptions = None, PlotOptions = pyPlots.defalultPO ,
                 SimulationSettings =  None, LoggerOptions = None):
        LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
        self.__Logger = pyLogger.getLogger(LoggerTag, LoggerOptions=LoggerOptions)
        self.__Logger.info('An instance of OpenDSS version ' + dss.__version__ + ' has ben created.')

        self.__dssPath = {
            'root': rootPath,
            'Import': rootPath + '/ProjectFiles/' + SimulationSettings['Active Project'] + '/PyDSS Settings',
            'Export': rootPath + '/Export',
            'dssFiles': rootPath + '/ProjectFiles/' + SimulationSettings['Active Project'] + '/DSSfiles',
        }

        self.__dssPath['pyPlots'] = self.__dssPath['Import'] + '/' + SimulationSettings['Active Scenario'] + '/pyPlotList'
        self.__dssPath['ExportLists'] = self.__dssPath['Import']+ '/'  + SimulationSettings['Active Scenario'] + '/ExportLists'
        self.__dssPath['pyControllers'] = self.__dssPath['Import']+ '/'  + SimulationSettings['Active Scenario'] + '/pyControllerList'

        self.__SimulationOptions = SimulationSettings
        self.__ResultOptions = ResultOptions
        self.__PlotOptions = PlotOptions
        self.__dssFilePath = self.__dssPath['dssFiles'] + '/' + SimulationSettings['DSS File']

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
                                      self.__dssObjects, self.__dssObjectsByClass, self.__dssBuses)

        pyCtrlReader = pcr(self.__dssPath['pyControllers'])
        ControllerList = pyCtrlReader.pyControllers
        if ControllerList is not None:
            self.__CreateControllers(ControllerList)


        pyPlotReader = ppr(self.__dssPath['pyPlots'])
        PlotList = pyPlotReader.pyPlots
        if PlotList is not None and not all(value == False for value in PlotOptions.values()):
            self.__CreatePlots(PlotList)

        for Plot in self.__pyPlotObjects:
            self.BokehSessionID = self.__pyPlotObjects[Plot].GetSessionID()
            if SimulationSettings['Open plots in browser']:
                self.__pyPlotObjects[Plot].session.show()
            break

        return

    def __ModifyNetwork(self):
        from NetworkModifier import Modifier
        # self.__Modifier = Modifier(dss, run_command, self.__SimulationOptions)
        #
        # self.__Modifier.Add_Elements('Storage', {'bus' : ['storagebus'], 'kWRated' : ['2000'], 'kWhRated'  : ['2000']},
        #                              True, self.__dssObjects)
        # #self.__Modifier.Edit_Elements('regcontrol', 'enabled' ,'False')
        #self.__Modifier.Edit_Elements('Load', 'enabled', 'False')
        return

    def __CreateControllers(self, ControllerDict):
        self.__pyControls = {}

        for ControllerType, ElementsDict in ControllerDict.items():
            for ElmName, SettingsDict in ElementsDict.items():
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
            PlotType2 = ['Sag plot', 'Histogram']
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

    def __UpdateControllers(self, Priority, Time, UpdateResults):
        error = 0
        for controller in self.__pyControls.values():
            error += controller.Update(Priority, Time, UpdateResults)
        return abs(error) < self.__SimulationOptions['Error tolerance'], error

    def __CreateBusObjects(self):
        BusNames = self.__dssCircuit.AllBusNames()
        for BusName in BusNames:
            self.__dssCircuit.SetActiveBus(BusName)
            self.__dssBuses[BusName] = dssBus(self.__dssInstance)
        return

    def __UpdateDictionary(self):
        InvalidSelection = ['Settings', 'ActiveClass', 'dss', 'utils', 'PDElements', 'XYCurves', 'Bus', 'Properties']
        self.__dssObjectsByClass={'LoadShape' : self.__GetRelaventObjectDict('LoadShape')}

        for ElmName in self.__dssInstance.Circuit.AllElementNames():
            Class, Name =  ElmName.split('.', 1)
            if Class + 's' not in self.__dssObjectsByClass:
                self.__dssObjectsByClass[Class + 's'] = {}
            self.__dssInstance.Circuit.SetActiveElement(ElmName)
            self.__dssObjectsByClass[Class + 's'][ElmName] = dssElement(self.__dssInstance)
            self.__dssObjects[ElmName] = self.__dssObjectsByClass[Class + 's'][ElmName]

        for ObjName in self.__dssObjects.keys():
            Class = ObjName.split('.')[0] + 's'
            if Class not in self.__dssObjectsByClass:
                self.__dssObjectsByClass[Class] = {}
            if  ObjName not in self.__dssObjectsByClass[Class]:
                self.__dssObjectsByClass[Class][ObjName] = self.__dssObjects[ObjName]

        self.__dssObjects['Circuit.' + self.__dssCircuit.Name()] = dssCircuit(self.__dssInstance)
        self.__dssObjectsByClass['Circuits'] = {
            'Circuit.' + self.__dssCircuit.Name() : self.__dssObjects['Circuit.' + self.__dssCircuit.Name()]
        }
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
        for step in range(Steps):
            print('Running simulation @ time step: ', step)
            self.__dssSolver.IncStep()
            for priority in range(CONTROLLER_PRIORITIES):
                for i in range(self.__SimulationOptions['Max Control Iterations']):
                    has_converged, error = self.__UpdateControllers(priority, step, UpdateResults=False)
                    self.__Logger.debug('Control Loop {} convergence error: {}'.format(priority, error))
                    if has_converged or i == self.__SimulationOptions['Max Control Iterations'] - 1:
                        if not has_converged:
                            self.__Logger.warning('Control Loop {} no convergence @ {} '.format(priority, step))
                        break
                    self.__dssSolver.reSolve()
                #self.__dssSolver.reSolve()

            self.__UpdatePlots()
            if self.__ResultOptions and self.__ResultOptions['Log Results']:
                self.ResultContainer.UpdateResults()
            #self.__dssSolver.IncStep()


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

        x = list(self.__Logger.handlers)
        for i in x:
            self.__Logger.removeHandler(i)
            i.flush()
            i.close()

        if self.__DelFlag == 1:
            self.__Logger.info('An intstance of OpenDSS (' + str(self) +') has been deleted.')
        else:
            self.__Logger.error('An intstance of OpenDSS (' + str(self) + ') crashed.')
        return
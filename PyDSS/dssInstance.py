from PyDSS.ResultContainer import ResultContainer as RC
from PyDSS.pyContrReader import pyContrReader as pcr
from PyDSS.pyPlotReader import pyPlotReader as ppr
from PyDSS.dssElement import dssElement
from PyDSS.dssCircuit import dssCircuit
from PyDSS.NetworkModifier import Modifier
from PyDSS.dssBus import dssBus
from PyDSS import SolveMode
from PyDSS import pyLogger

from PyDSS.pyPostprocessor import pyPostprocess
import PyDSS.pyControllers as pyControllers
import PyDSS.pyPlots as pyPlots


from PyDSS.Extensions.NetworkGraph import CreateGraph

import numpy as np
import logging
import time
import os

from bokeh.plotting import curdoc
from bokeh.layouts import row
from bokeh.client import push_session

CONTROLLER_PRIORITIES = 3

class OpenDSS:
    def __init__(self, **kwargs):
        from opendssdirect.utils import run_command
        import opendssdirect as dss

        self._TempResultList = []
        self._dssInstance = dss
        self._dssBuses = {}
        self._dssObjects = {}
        self._dssObjectsByClass = {}
        self._DelFlag = 0
        self._pyPlotObjects = {}
        self.BokehSessionID = None

        rootPath = kwargs['Project Path']
        self._ActiveProject = kwargs['Active Project']
        importPath = os.path.join(rootPath, kwargs['Active Project'], 'PyDSS Scenarios')
        self._dssPath = {
            'root': rootPath,
            'Import': importPath,
            'pyPlots': os.path.join(importPath, kwargs['Active Scenario'], 'pyPlotList'),
            'ExportLists': os.path.join(importPath, kwargs['Active Scenario'], 'ExportLists'),
            'pyControllers': os.path.join(importPath, kwargs['Active Scenario'], 'pyControllerList'),
            'Export': os.path.join(rootPath, kwargs['Active Project'], 'Exports'),
            'Log': os.path.join(rootPath, kwargs['Active Project'], 'Logs'),
            'dssFiles': os.path.join(rootPath, kwargs['Active Project'], 'DSSfiles'),
            'dssFilePath': os.path.join(rootPath, kwargs['Active Project'], 'DSSfiles', kwargs['DSS File']),
        }

        LoggerTag = kwargs['Active Project'] + '_' + kwargs['Active Scenario']
        self._Logger = pyLogger.getLogger(LoggerTag, self._dssPath['Log'], LoggerOptions=kwargs)
        self._Logger.info('An instance of OpenDSS version ' + dss.__version__ + ' has been created.')

        for key, path in self._dssPath.items():
            assert (os.path.exists(path)), '{} path: {} does not exist!'.format(key, path)

        self._Options = kwargs
        self._dssInstance.Basic.ClearAll()
        self._dssInstance.utils.run_command('Log=NO')
        run_command('Clear')
        self._Logger.info('Loading OpenDSS model')
        reply = run_command('compile ' + self._dssPath['dssFilePath'])
        self._Logger.info('OpenDSS:  ' + reply)

        assert ('error ' not in reply.lower()), 'Error compiling OpenDSS model.\n{}'.format(reply)
        run_command('Set DefaultBaseFrequency={}'.format(self._Options['Fundamental frequency']))
        self._Logger.info('OpenDSS fundamental frequency set to :  ' + str(self._Options['Fundamental frequency']) + ' Hz')

        run_command('Set %SeriesRL={}'.format(self._Options['Percentage load in series']))
        if self._Options['Neglect shunt admittance']:
            run_command('Set NeglectLoadY=Yes')

        self._dssCircuit = dss.Circuit
        self._dssElement = dss.Element
        self._dssBus = dss.Bus
        self._dssClass = dss.ActiveClass
        self._dssCommand = run_command
        self._dssSolution = dss.Solution
        self._dssSolver = SolveMode.GetSolver(SimulationSettings=kwargs, dssInstance=self._dssInstance)

        self._Modifier = Modifier(dss, run_command, self._Options)
        self._UpdateDictionary()
        self._CreateBusObjects()
        self._dssSolver.reSolve()

        if self._Options and self._Options['Log Results']:
            self.ResultContainer = RC(kwargs, self._dssPath,  self._dssObjects, self._dssObjectsByClass,
                                      self._dssBuses, self._dssSolver, self._dssCommand)

        pyCtrlReader = pcr(self._dssPath['pyControllers'])
        ControllerList = pyCtrlReader.pyControllers
        if ControllerList is not None:
            self._CreateControllers(ControllerList)

        if kwargs['Create dynamic plots']:
            pyPlotReader = ppr(self._dssPath['pyPlots'])
            PlotList = pyPlotReader.pyPlots
            self._CreatePlots(PlotList)
            for Plot in self._pyPlotObjects:
                self.BokehSessionID = self._pyPlotObjects[Plot].GetSessionID()
                if kwargs['Open plots in browser']:
                    self._pyPlotObjects[Plot].session.show()
                break
        return

    def _ModifyNetwork(self):
        # self._Modifier.Add_Elements('Storage', {'bus' : ['storagebus'], 'kWRated' : ['2000'], 'kWhRated'  : ['2000']},
        #                              True, self._dssObjects)
        # self._Modifier.Edit_Elements('regcontrol', 'enabled' ,'False')
        #self._Modifier.Edit_Elements('Load', 'enabled', 'False')
        return

    def _CreateControllers(self, ControllerDict):
        self._pyControls = {}

        for ControllerType, ElementsDict in ControllerDict.items():
            for ElmName, SettingsDict in ElementsDict.items():
                 Controller = pyControllers.pyController.Create(ElmName, ControllerType, SettingsDict, self._dssObjects,
                                                  self._dssInstance, self._dssSolver)
                 if Controller != -1:
                    self._pyControls['Controller.' + ElmName] = Controller
                    self._Logger.info('Created pyController -> Controller.' + ElmName)
        return

    def _CreatePlots(self, PlotsDict):

        self.BokehDoc = curdoc()
        Figures = []
        for PlotType, PlotNames in PlotsDict.items():
            newPlotNames = list(PlotNames)
            PlotType1= ['Topology', 'GISplot']
            PlotType2 = ['SagPlot', 'Histogram']
            PlotType3 = ['XYPlot', 'TimeSeries', 'FrequencySweep']

            for Name in newPlotNames:
                PlotSettings = PlotNames[Name]
                PlotSettings['FileName'] = Name
                if PlotType in PlotType1:

                    self._pyPlotObjects[PlotType] = pyPlots.pyPlots.Create(
                        PlotType,
                        PlotSettings,
                        self._dssBuses,
                        self._dssObjectsByClass,
                        self._dssCircuit,
                        self._dssSolver
                    )
                    Figures.append(self._pyPlotObjects[PlotType].GetFigure())
                    #self.BokehDoc.add_root(self._pyPlotObjects[PlotType].GetFigure())
                    self._Logger.info('Created pyPlot -> ' + PlotType)
                elif PlotType in PlotType2:
                    self._pyPlotObjects[PlotType + Name] = pyPlots.pyPlots.Create(
                        PlotType,
                        PlotSettings,
                        self._dssBuses,
                        self._dssObjectsByClass,
                        self._dssCircuit,
                        self._dssSolver
                    )
                    self._Logger.info('Created pyPlot -> ' + PlotType)
                elif PlotType in PlotType3:
                    self._pyPlotObjects[PlotType+Name] = pyPlots.pyPlots.Create(
                        PlotType,
                        PlotSettings,
                        self._dssBuses,
                        self._dssObjects,
                        self._dssCircuit,
                        self._dssSolver
                    )
                    self._Logger.info('Created pyPlot -> ' + PlotType)

        Layout = row(*Figures)
        self.BokehDoc.add_root(Layout)
        self.BokehDoc.title = "PyDSS"
        self.session = push_session(self.BokehDoc)
        self.session.show()
        return

    def _UpdateControllers(self, Priority, Time, UpdateResults):
        error = 0

        for controller in self._pyControls.values():
            error += controller.Update(Priority, Time, UpdateResults)
            if Priority == 0:
                pass
        return abs(error) < self._Options['Error tolerance'], error

    def _CreateBusObjects(self):
        BusNames = self._dssCircuit.AllBusNames()
        self._dssInstance.run_command('New  Fault.DEFAULT Bus1={} enabled=no r=0.01'.format(BusNames[0]))
        for BusName in BusNames:
            self._dssCircuit.SetActiveBus(BusName)
            self._dssBuses[BusName] = dssBus(self._dssInstance)
        return

    def _UpdateDictionary(self):
        InvalidSelection = ['Settings', 'ActiveClass', 'dss', 'utils', 'PDElements', 'XYCurves', 'Bus', 'Properties']
        self._dssObjectsByClass={'LoadShape': self._GetRelaventObjectDict('LoadShape')}

        for ElmName in self._dssInstance.Circuit.AllElementNames():
            Class, Name =  ElmName.split('.', 1)
            if Class + 's' not in self._dssObjectsByClass:
                self._dssObjectsByClass[Class + 's'] = {}
            self._dssInstance.Circuit.SetActiveElement(ElmName)
            self._dssObjectsByClass[Class + 's'][ElmName] = dssElement(self._dssInstance)
            self._dssObjects[ElmName] = self._dssObjectsByClass[Class + 's'][ElmName]

        for ObjName in self._dssObjects.keys():
            Class = ObjName.split('.')[0] + 's'
            if Class not in self._dssObjectsByClass:
                self._dssObjectsByClass[Class] = {}
            if  ObjName not in self._dssObjectsByClass[Class]:
                self._dssObjectsByClass[Class][ObjName] = self._dssObjects[ObjName]

        self._dssObjects['Circuit.' + self._dssCircuit.Name()] = dssCircuit(self._dssInstance)
        self._dssObjectsByClass['Circuits'] = {
            'Circuit.' + self._dssCircuit.Name(): self._dssObjects['Circuit.' + self._dssCircuit.Name()]
        }
        return

    def _GetRelaventObjectDict(self, key):
        ObjectList = {}
        ElmCollection = getattr(self._dssInstance, key)
        Elem = ElmCollection.First()
        while Elem:
            ObjectList[self._dssInstance.Element.Name()] =  dssElement(self._dssInstance)
            Elem = ElmCollection.Next()
        return ObjectList

    def RunStep(self, step, updateObjects=None):

        if updateObjects:
            for object, params in updateObjects.items():
                cl, name = object.split('.')
                self._Modifier.Edit_Element(cl, name, params)
            pass

        self._dssSolver.IncStep()
        if self._Options['Co-simulation Mode']:
            self.ResultContainer.updateSubscriptions()

        if self._Options['Disable PyDSS controllers'] is False:
            for priority in range(CONTROLLER_PRIORITIES):
                for i in range(self._Options['Max Control Iterations']):
                    has_converged, error = self._UpdateControllers(priority, step, UpdateResults=False)
                    self._Logger.debug('Control Loop {} convergence error: {}'.format(priority, error))
                    if has_converged or i == self._Options['Max Control Iterations'] - 1:
                        if not has_converged:
                            self._Logger.warning('Control Loop {} no convergence @ {} '.format(priority, step))
                        break
                    self._dssSolver.reSolve()

            self._UpdatePlots()
            if self._Options['Log Results']:
                self.ResultContainer.UpdateResults()
            if self._Options['Return Results']:
                return self.ResultContainer.CurrentResults

        if self._Options['Enable frequency sweep'] and self._Options['Simulation Type'].lower() != 'dynamic':
            self._dssSolver.setMode('Harmonic')
            for freqency in np.arange(self._Options['Start frequency'], self._Options['End frequency'] + 1,
                                      self._Options['frequency increment']):
                self._dssSolver.setFrequency(freqency * self._Options['Fundamental frequency'])
                self._dssSolver.reSolve()
                self._UpdatePlots()
                if self._Options['Log Results']:
                    self.ResultContainer.UpdateResults()
            if self._Options['Simulation Type'].lower() == 'snapshot':
                self._dssSolver.setMode('Snapshot')
            else:
                self._dssSolver.setMode('Yearly')
        return

    def RunSimulation(self, file_prefix=''):
        startTime = time.time()
        Steps, sTime, eTime = self._dssSolver.SimulationSteps()
        self._Logger.info('Running simulation from {} till {}.'.format(sTime, eTime))
        self._Logger.info('Simulation time step {}.'.format(Steps))

        if self._Options['Post processing script'] != "":
            self.postprocessor = pyPostprocess.Create(self._dssInstance, self._dssSolver, self._dssObjects,
                                                     self._dssObjectsByClass, self._Options)
        else:
            print('No post processing script selected')
            self.postprocessor = None

        step = 0
        while step < Steps:
            self.RunStep(step)
            if self.postprocessor is not None:
                step = self.postprocessor.run(step, Steps)
            step+=1

        if self._Options and self._Options['Log Results']:
            self.ResultContainer.ExportResults(file_prefix)

        self._Logger.info('Simulation completed in ' + str(time.time() - startTime) + ' seconds')
        self._Logger.info('End of simulation')

    def RunMCsimulation(self, samples):
        from PyDSS.Extensions.MonteCarlo import MonteCarloSim
        MC = MonteCarloSim(self._Options, self._dssPath, self._dssObjects, self._dssObjectsByClass)
        for i in range(samples):
            MC.Create_Scenario()
            self.RunSimulation('MC{}'.format(i))
        return

    def _UpdatePlots(self):
        for Plot in self._pyPlotObjects:
            self._pyPlotObjects[Plot].UpdatePlot()
        return

    def CreateGraph(self, Visualize=False):
        self._Logger.info('Creating graph representation')
        defaultGraphPlotSettings = {
                'Layout'                 : 'Circular', # Shell, Circular, Fruchterman
                'Iterations'             : 100,
                'ShowRefNode'            : False,
                'NodeSize'               : None, #None for auto fit
                'LineColorProperty'      : 'Class',
                'NodeColorProperty'      : 'ConnectedPCs',
                'Open plots in browser'  : True,
                'OutputPath'             : self._dssPath['Export'],
                'OutputFile'             : None
        }
        defaultGraphPlotSettings['OutputFile'] = self._ActiveProject + \
                                                  '_' + defaultGraphPlotSettings['LineColorProperty'] + \
                                                  '_' + defaultGraphPlotSettings['NodeColorProperty'] + \
                                                  '_' + defaultGraphPlotSettings['Layout'] + '.html'

        Graph = CreateGraph(self._dssInstance)
        if Visualize:
            Graph.CreateGraphVisualization(defaultGraphPlotSettings)
        return Graph.Get()

    def __del__(self):
        self._Logger.info('An instance of OpenDSS (' + str(self) + ') has been deleted.')
        if self._Options["Log to external file"]:
            handlers = list(self._Logger.handlers)
            for filehandler in handlers:
                filehandler.flush()
                filehandler.close()
                self._Logger.removeHandler(filehandler)
        return

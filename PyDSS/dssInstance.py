from PyDSS.ResultContainer import ResultContainer as RC
from PyDSS.ResultData import ResultData
from PyDSS.pyContrReader import pyContrReader as pcr
from PyDSS.pyContrReader import read_controller_settings_from_registry
from PyDSS.pyPlotReader import pyPlotReader as ppr
from PyDSS.dssElementFactory import create_dss_element
from PyDSS.dssCircuit import dssCircuit
from PyDSS.exceptions import PyDssConvergenceError, PyDssConvergenceErrorCountExceeded, \
    PyDssConvergenceMaxError, OpenDssModelError
from PyDSS.NetworkModifier import Modifier
from PyDSS.dssBus import dssBus
from PyDSS import SolveMode
from PyDSS import pyLogger
from PyDSS import helics_interface as HI
from PyDSS.utils.dataframe_utils import write_dataframe
from PyDSS.utils.utils import make_human_readable_size

from PyDSS.exceptions import InvalidParameter, InvalidConfiguration

from PyDSS.pyPostprocessor import pyPostprocess
import PyDSS.pyControllers as pyControllers
import PyDSS.pyPlots as pyPlots

import numpy as np
import pandas as pd
import logging
import time
import os

from bokeh.plotting import curdoc
from bokeh.layouts import row
from bokeh.client import push_session
from opendssdirect.utils import run_command
import opendssdirect as dss


CONTROLLER_PRIORITIES = 3

class OpenDSS:
    def __init__(self, params):
        self._TempResultList = []
        self._dssInstance = dss
        self._dssBuses = {}
        self._dssObjects = {}
        self._dssObjectsByClass = {}
        self._DelFlag = 0
        self._pyPlotObjects = {}
        self.BokehSessionID = None
        self._Options = params
        self._convergenceErrors = 0
        self._maxConvergenceErrorCount = 0
        self._maxConvergenceError = 0.0

        rootPath = params['Project']['Project Path']
        self._ActiveProject = params['Project']['Active Project']
        importPath = os.path.join(rootPath, params['Project']['Active Project'], 'Scenarios')

        self._dssPath = {
            'root': rootPath,
            'Import': importPath,
            'pyPlots': os.path.join(importPath, params['Project']['Active Scenario'], 'pyPlotList'),
            'ExportLists': os.path.join(importPath, params['Project']['Active Scenario'], 'ExportLists'),
            'pyControllers': os.path.join(importPath, params['Project']['Active Scenario'], 'pyControllerList'),
            'Export': os.path.join(rootPath, params['Project']['Active Project'], 'Exports'),
            'Log': os.path.join(rootPath, params['Project']['Active Project'], 'Logs'),
            'dssFiles': os.path.join(rootPath, params['Project']['Active Project'], 'DSSfiles'),
            'dssFilePath': os.path.join(rootPath, params['Project']['Active Project'], 'DSSfiles', params['Project']['DSS File']),
        }

        if params['Project']['DSS File Absolute Path']:
            self._dssPath['dssFilePath'] = params['Project']['DSS File']
        else:
            self._dssPath['dssFilePath'] = os.path.join(
                rootPath,
                params['Project']['Active Project'],
                'DSSfiles',
                params['Project']['DSS File']
            )

        if params["Logging"]["Pre-configured logging"]:
            self._Logger = logging.getLogger(__name__)
        else:
            LoggerTag = pyLogger.getLoggerTag(params)
            self._Logger = pyLogger.getLogger(LoggerTag, self._dssPath['Log'], LoggerOptions=params["Logging"])
        self._Logger.info('An instance of OpenDSS version ' + dss.__version__ + ' has been created.')

        for key, path in self._dssPath.items():
            assert (os.path.exists(path)), '{} path: {} does not exist!'.format(key, path)

        self._dssInstance.Basic.ClearAll()
        self._dssInstance.utils.run_command('Log=NO')
        run_command('Clear')
        self._Logger.info('Loading OpenDSS model')
        try:
            orig_dir = os.getcwd()
            reply = run_command('compile ' + self._dssPath['dssFilePath'])
        finally:
            os.chdir(orig_dir)
        self._Logger.info('OpenDSS:  ' + reply)

        if reply != "":
            raise OpenDssModelError(f"Error compiling OpenDSS model: {reply}")

        run_command('Set DefaultBaseFrequency={}'.format(params['Frequency']['Fundamental frequency']))
        self._Logger.info('OpenDSS fundamental frequency set to :  ' + str(params['Frequency']['Fundamental frequency']) + ' Hz')

        # TODO: This command doesn't work on any version. Starting in opendssdirect.py v0.5.0 it causes
        # a fatal exception.
        #run_command('Set %SeriesRL={}'.format(params['Frequency']['Percentage load in series']))
        if params['Frequency']['Neglect shunt admittance']:
            run_command('Set NeglectLoadY=Yes')

        self._dssCircuit = dss.Circuit
        self._dssElement = dss.Element
        self._dssBus = dss.Bus
        self._dssClass = dss.ActiveClass
        self._dssCommand = run_command
        self._dssSolution = dss.Solution
        self._dssSolver = SolveMode.GetSolver(SimulationSettings=params, dssInstance=self._dssInstance)

        self._Modifier = Modifier(dss, run_command, params)
        self._UpdateDictionary()
        self._CreateBusObjects()
        self._dssSolver.reSolve()

        if params and params['Exports']['Log Results']:
            if params['Exports']['Result Container'] == 'ResultContainer':
                self.ResultContainer = RC(params, self._dssPath,  self._dssObjects, self._dssObjectsByClass,
                                          self._dssBuses, self._dssSolver, self._dssCommand)
            else:
                self.ResultContainer = ResultData(params, self._dssPath,  self._dssObjects, self._dssObjectsByClass,
                                                    self._dssBuses, self._dssSolver, self._dssCommand, self._dssInstance)
        else:
            self.ResultContainer = None

        if params['Project']['Use Controller Registry']:
            ControllerList = read_controller_settings_from_registry(self._dssPath['pyControllers'])
        else:
            pyCtrlReader = pcr(self._dssPath['pyControllers'])
            ControllerList = pyCtrlReader.pyControllers

        if ControllerList is not None:
            self._CreateControllers(ControllerList)

        if params['Plots']['Create dynamic plots']:
            pyPlotReader = ppr(self._dssPath['pyPlots'])
            PlotList = pyPlotReader.pyPlots
            self._CreatePlots(PlotList)
            for Plot in self._pyPlotObjects:
                self.BokehSessionID = self._pyPlotObjects[Plot].GetSessionID()
                if params['Plots']['Open plots in browser']:
                    self._pyPlotObjects[Plot].session.show()
                break
        self._increment_flag = True
        if params['Helics']["Co-simulation Mode"]:
            self._HI = HI.helics_interface(self._dssSolver, self._dssObjects, self._dssObjectsByClass, params,
                                           self._dssPath)
        return

    def _ReadControllerDefinitions(self):
        controllers = None
        mappings = os.path.join(os.path.dirname(self._dssPath['pyControllers']), "ControllerMappings")
        if os.path.exists(mappings):
            ctrl_mapping_files = os.listdir(self._dssPath["ControllerMappings"])
            for filename in ctrl_mapping_files: 
                data = load_data(os.path.join(self._dssPath["ControllerMappings"], filename))

        return controllers

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
            PlotType1= ['Topology', 'GISplot', 'NetworkGraph']
            PlotType2 = ['SagPlot', 'Histogram']
            PlotType3 = ['XY', 'TimeSeries', 'FrequencySweep']

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

    def _RunPostProcessors(self, step, Steps, postprocessors):
        for postprocessor in postprocessors:
            orig_step = step
            step, has_converged, error = postprocessor.run(step, Steps)
            assert step <= orig_step, "step cannot increment in postprocessor"
            if not has_converged:
                name = postprocessor.__class__.__name__
                self._Logger.warn("postprocessor %s reported a convergence error at step %s", name, step)
                self._HandleConvergenceErrorChecks(step, error)

        return step, has_converged

    def _RunUpdateControllers(self, step):
        time_step_has_converged = True
        for priority in range(CONTROLLER_PRIORITIES):
            priority_has_converged = False
            for _ in range(self._Options["Project"]["Max Control Iterations"]):
                has_converged, error = self._UpdateControllers(priority, step, UpdateResults=False)
                if has_converged:
                    priority_has_converged = True
                    break
                self._Logger.debug("Control Loop {} convergence error: {}".format(priority, error))
                self._dssSolver.reSolve()
            if not priority_has_converged:
                time_step_has_converged = False
                self._Logger.warning("Control Loop %s no convergence @ %s error=%s", priority, step, error)
                self._HandleConvergenceErrorChecks(step, error)

        return time_step_has_converged

    def _HandleConvergenceErrorChecks(self, step, error):
        self._convergenceErrors += 1

        if self._maxConvergenceError != 0.0 and error > self._maxConvergenceError:
            self._Logger.error("Convergence error %s exceeded max value %s at step %s", error, self._maxConvergenceError, step)
            raise PyDssConvergenceMaxError(f"Exceeded max convergence error {error}")

        if self._maxConvergenceErrorCount != 0 and self._convergenceErrors > self._maxConvergenceErrorCount:
            self._Logger.error("Exceeded convergence error count threshold at step %s", step)
            raise PyDssConvergenceErrorCountExceeded(f"{self._convergenceErrors} errors occurred")

    def _UpdateControllers(self, Priority, Time, UpdateResults):
        maxError = 0.0

        for controller in self._pyControls.values():
            error = abs(controller.Update(Priority, Time, UpdateResults))
            if error > maxError:
                maxError = error
        return maxError < self._Options['Project']['Error tolerance'], maxError

    def _CreateBusObjects(self):
        BusNames = self._dssCircuit.AllBusNames()
        self._dssInstance.run_command('New  Fault.DEFAULT Bus1={} enabled=no r=0.01'.format(BusNames[0]))
        for BusName in BusNames:
            self._dssCircuit.SetActiveBus(BusName)
            self._dssBuses[BusName] = dssBus(self._dssInstance)
        return

    def _UpdateDictionary(self):
        InvalidSelection = ['Settings', 'ActiveClass', 'dss', 'utils', 'PDElements', 'XYCurves', 'Bus', 'Properties']
        # TODO: this causes a segmentation fault. Aadil says it may not be needed.
        #self._dssObjectsByClass={'LoadShape': self._GetRelaventObjectDict('LoadShape')}

        for ElmName in self._dssInstance.Circuit.AllElementNames():
            Class, Name =  ElmName.split('.', 1)
            if Class + 's' not in self._dssObjectsByClass:
                self._dssObjectsByClass[Class + 's'] = {}
            self._dssInstance.Circuit.SetActiveElement(ElmName)
            self._dssObjectsByClass[Class + 's'][ElmName] = create_dss_element(Class, Name, self._dssInstance)
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
            FullName = self._dssInstance.Element.Name()
            Class, Name =  FullName.split('.', 1)
            ObjectList[FullName] = create_dss_element(Class, Name, self._dssInstance)
            Elem = ElmCollection.Next()
        return ObjectList

    def RunStep(self, step, updateObjects=None):
        # updating paramters bebore simulation run

        if self._Options['Helics']['Co-simulation Mode']:
            if self._increment_flag:
                self._dssSolver.IncStep()
            else:
                self._dssSolver.reSolve()
            self._HI.updateHelicsSubscriptions()
        else:
            self._dssSolver.IncStep()
            if updateObjects:
                for object, params in updateObjects.items():
                    cl, name = object.split('.')
                    self._Modifier.Edit_Element(cl, name, params)


        # run simulation time step and get results
        has_converged = True
        if not self._Options['Project']['Disable PyDSS controllers']:
            has_converged = self._RunUpdateControllers(step)
            self._UpdatePlots()

        if self._Options['Frequency']['Enable frequency sweep'] and \
                self._Options['Project']['Simulation Type'].lower() != 'dynamic':
            self._dssSolver.setMode('Harmonic')
            for freqency in np.arange(self._Options['Frequency']['Start frequency'],
                                      self._Options['Frequency']['End frequency'] + 1,
                                      self._Options['Frequency']['frequency increment']):
                self._dssSolver.setFrequency(freqency * self._Options['Frequency']['Fundamental frequency'])
                self._dssSolver.reSolve()
                self._UpdatePlots()
                if self._Options['Exports']['Log Results']:
                    self.ResultContainer.UpdateResults()
            if self._Options['Project']['Simulation Type'].lower() == 'snapshot':
                self._dssSolver.setMode('Snapshot')
            else:
                self._dssSolver.setMode('Yearly')

        if self._Options['Helics']['Co-simulation Mode']:
            self._HI.updateHelicsPublications()
            self._increment_flag, helics_time = self._HI.request_time_increment()

        return has_converged

    def DryRunSimulation(self, project, scenario):
        """Run one time point for getting estimated space."""
        if not self._Options['Exports']['Log Results']:
            raise InvalidConfiguration("Log Reults must set to be True.")

        Steps, _, _ = self._dssSolver.SimulationSteps()
        self._Logger.info('Dry run simulation...')
        self.ResultContainer.InitializeDataStore(project.hdf_store, Steps)

        try:
            self.RunStep(0)
            self._ProcessStepResults(0, 1, True, [])
        finally:
            self.ResultContainer.Close()

        return self.ResultContainer.max_num_bytes()

    def RunSimulation(self, project, scenario, MC_scenario_number=None):
        startTime = time.time()
        Steps, sTime, eTime = self._dssSolver.SimulationSteps()
        self._maxConvergenceErrorCount = round(self._Options['Project']['Convergence error percent threshold'] * .01 * Steps)
        self._maxConvergenceError = self._Options['Project']['Max error tolerance']
        dss.Solution.Convergence(self._Options['Project']['Error tolerance'])
        self._Logger.info('Running simulation from {} till {}.'.format(sTime, eTime))
        self._Logger.info('Simulation time step {}.'.format(Steps))
        self._Logger.info('Max convergence error count {}.'.format(self._maxConvergenceErrorCount))
        if self._Options['Exports']['Result Container'] == 'ResultData' and self.ResultContainer is not None:
            self.ResultContainer.InitializeDataStore(project.hdf_store, Steps, MC_scenario_number)

        postprocessors = [
            pyPostprocess.Create(
                project,
                scenario,
                ppInfo,
                self._dssInstance,
                self._dssSolver,
                self._dssObjects,
                self._dssObjectsByClass,
                self._Options,
                self._Logger,
            ) for ppInfo in scenario.post_process_infos
        ]
        if not postprocessors:
            self._Logger.info('No post processing script selected')

        try:
            step = 0
            while step < Steps:
                pydss_has_converged = self.RunStep(step)
                opendss_has_converged = dss.Solution.Converged()
                if not opendss_has_converged:
                    self._Logger.info("OpenDSS did not converge at step=%s pydss_converged=%s",
                                      step, pydss_has_converged)
                has_converged = pydss_has_converged and opendss_has_converged
                step = self._ProcessStepResults(step, Steps, has_converged, postprocessors)
                if self._increment_flag:
                    step += 1
                self._dssSolver.IncrementTimeStep()
        finally:
		    
            if self._Options and self._Options['Exports']['Log Results']:
                # This is here to guarantee that DatasetBuffers aren't left
                # with any data in memory.
                self.ResultContainer.Close()
				
            for postprocessor in postprocessors: 
                postprocessor.finalize()
				
        if self._Options and self._Options['Exports']['Log Results']:
            self.ResultContainer.ExportResults(
                fileprefix="",
            )

        self._Logger.info('Simulation completed in ' + str(time.time() - startTime) + ' seconds')
        self._Logger.info('End of simulation')

    def _ProcessStepResults(self, step, Steps, has_converged, postprocessors):
        if self.ResultContainer is not None and step == 0:
            size = make_human_readable_size(self.ResultContainer.max_num_bytes())
            self._Logger.info('Storage requirement estimation: %s, estimated based on first time step run.', size)

        if postprocessors:
            step, converged = self._RunPostProcessors(step, Steps, postprocessors)
            if not converged:
                has_converged = False

        if self._Options['Exports']['Log Results']:
            if not has_converged and self._Options['Project']['Skip export on convergence error']:
                store_nan = True
            else:
                store_nan = False
            self.ResultContainer.UpdateResults(store_nan=store_nan)

        return step

    def RunMCsimulation(self, project, scenario, samples):
        from PyDSS.Extensions.MonteCarlo import MonteCarloSim
        MC = MonteCarloSim(self._Options, self._dssPath, self._dssObjects, self._dssObjectsByClass)
        for i in range(samples):
            MC.Create_Scenario()
            self.RunSimulation(project, scenario, i)
        return

    def _UpdatePlots(self):
        for Plot in self._pyPlotObjects:
            self._pyPlotObjects[Plot].UpdatePlot()
        return

    def __del__(self):
        if self._Options["Logging"]["Log to external file"]:
            handlers = list(self._Logger.handlers)
            for filehandler in handlers:
                filehandler.flush()
                filehandler.close()
                self._Logger.removeHandler(filehandler)
        return

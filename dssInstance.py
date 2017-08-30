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
    print 'An instance of OpenDSS version ' + dss.__version__ + ' has ben created.'
    __dssInstance = dss
    __dssBuses = {}
    __dssObjects = {}
    __dssObjectsByClass = {}
    __DelFlag = 0
    __pyPlotObjects = {}
    def __init__(self , SimType = 'rSnapshot', rootPath = os.getcwd(), dssMainFile = 'MasterCircuit_C591.dss',
                 ExportList = {}, ControllerList = None, PlotList = None):

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
        self.__UpdateDictionary()
        self.__CreateBusObjects()
        self.__dssSolver = SolveMode.GetSolver(SimType, self.__dssInstance)
        self.__TempResultList = []

        self.__PrepareExportList(ExportList)
        if ControllerList is not None and isinstance(ControllerList, dict):
            self.__CreateControllers(ControllerList)
            self.__dssSolver.customControlLoop = self.__UpdateControllers

        self.__CreatePlots(PlotList)

        return

    def __CreateControllers(self,ControllerDict):
        self.__pyControls = {}
        for ControllerType, ElmNames in ControllerDict.iteritems():
            for ElmName in ElmNames:
                 Controller = pyController.Create(ElmName, ControllerType, self.__dssObjects)
                 if Controller != -1:
                    self.__pyControls['Controller.' + ElmName] = Controller
        return


    def __CreatePlots(self, PlotsDict):
        __pyPlotObjects= {}
        for PlotType, PlotSettings in PlotsDict.iteritems():
            if PlotSettings == None:
                self.__pyPlotObjects[PlotType] = pyPlots.Create(PlotType, None,
                                                self.__dssBuses, self.__dssObjectsByClass)
            else:
                self.__pyPlotObjects[PlotType+str(PlotSettings)] = pyPlots.Create(PlotType, PlotSettings,
                                                                self.__dssBuses, self.__dssObjectsByClass)
        return

    def __UpdateControllers(self):
        for Key, Controller in self.__pyControls.iteritems():
            Controller.Update()
        return

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

    def RunSimulation(self, Steps):
        startTime = time.time()
        for i in range(Steps):
            self.__dssSolver.IncStep(i)
            #print self.__dssBuses['loadbus'].GetVariable('Voltages')
            self.__UpdateResults()

        self.__ExportResults = pd.DataFrame(self.__TempResultList, columns = self.__ExportResults.columns)
        #print self.__ExportResults
        print 'Simulation completed in ' + str(time.time() - startTime) + ' seconds'
        print 'End of simulation'

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
            print 'An intstance of OpenDSS (' + str(self) +') has been deleted.'
        else:
            print 'An intstance of OpenDSS (' + str(self) + ') crashed.'
        return


EL = {
    'Loads':['Voltages','Enabled'],
    'Lines':['CurrentsMagAng']
}

CL = {
    'LoadController': ['Load.load1'],
}

PL = {
    'Network layout': { 'FileName': 'Network layout.html',
                        'Path' : None,
                        'Width' : 800,
                        'Height' : 600
                        },
}

DSS = OpenDSS(SimType = 'Snapshot' , ExportList = EL, ControllerList = CL, PlotList = PL )
#DSS.RunSimulation(3000)
DSS.DeleteInstance()
os.system("pause")
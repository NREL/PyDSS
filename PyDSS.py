from PyQt5.QtWidgets import QApplication, QDialog, QListWidgetItem, QTableWidgetItem, QSizePolicy
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import subprocess

#w.load(QtCore.QUrl('https://www.archlinux.org/'))

from dssGUI import Ui_PyDSS
import pandas as pd
import dssInstance
import logging
import sys
import os
#******************************************************************
import matplotlib
matplotlib.use("Qt5Agg")
#******************************************************************
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

#*************

font = {'family': 'sherif',
        'color':  'black',
        'weight': 'normal',
        'size': 12,
        }


class PyDSS():
    def __init__(self):
        self.dssPath = os.getcwd()
        self.window = QDialog()
        self.ui = Ui_PyDSS()
        self.ui.setupUi(self.window)
        self.timer = QtCore.QTimer(self.window)
        self.timer.setInterval(500)
        self.timer.stop()
        self.timer.timeout.connect(self.TimeLapsed)

        #self.ui.WebViewer.


        self.CreateMPLembeddedPlot()
        self.PopulateProjectsList()
        self.ui.listWidget_opendssfiles.clicked.connect(self.GetMainDSSfile)
        self.ui.pushButton_RunSimulation.clicked.connect(self.RunSimulation)
        self.ui.pushButton_Exit.clicked.connect(self.ExitPyDSS)



        return

    def CreateMPLembeddedPlot(self):
        self.MLPplot = PlotCanvas(self.ui.tab_15, width=7.8, height=5.4)
        self.MLPplot.move(280, 30)

    def ExitPyDSS(self):
        quit()
        return

    def RunSimulation(self):
        RO = {
            'Log Results'            : True if str(self.ui.comboBox_ExportResults.currentText()) == 'True' else False,
            'Export Mode'            : str(self.ui.comboBox_ExportMode.currentText()),  # 'byClass'        , 'byElement'
            'Export Style'           : str(self.ui.comboBox_ExportStyle.currentText()),  # 'Seperate files' , 'Single file'
        }
        #print(RO)
        # Plot Settings
        PO = {
            'Network layout'         : True if self.ui.checkBox_NetworkLayout.isChecked() else False,
            'Time series'            : True if self.ui.checkBox_TimeSeries.isChecked() else False,
            'XY plot'                : True if self.ui.checkBox_XY.isChecked() else False,
            'Sag plot'               : True if self.ui.checkBox_VD.isChecked() else False,
            'Histogram'              : True if self.ui.checkBox_Histogram.isChecked() else False,
            'GIS overlay'            : True if self.ui.checkBox_GIS.isChecked() else False,
        }
        #print(PO)
        # Simulation Settings
        SS = {
            'Start Day'              : self.ui.spinBox_StartDay.value(),
            'End Day'                : self.ui.spinBox_EndDay.value(),
            'Step resolution (min)'  : self.ui.spinBox_TimeStep.value(),
            'Max Control Iterations' : self.ui.spinBox_MaxItr.value(),
            'Error tolerance'        : self.ui.doubleSpinBox.value(),
            'Simulation Type'        : self.GetSimulationType(),
            'Active Project'         : self.ActiveProject,
            'Active Scenario'        : self.ActiveScenario,
            'DSS File'               : self.MainDSSfile,
            'Open plots in browser'  : False,
        }
        #print(SS)
        # Logger settings
        LO = {
            'Logging Level'          : self.GetLoggingLevel(),
            'Log to external file'   : True if str(self.ui.comboBox_LogExtFile.currentText()) == 'True' else False,
            'Display on screen'      : True if str(self.ui.comboBox_LogScreen.currentText()) == 'True' else False,
            'Clear old log files'    : True if str(self.ui.comboBox_DelLog.currentText()) == 'True' else False,
        }
        global BokehSessionID
        BokehSessionID = ''
        global InstanceCreated
        InstanceCreated = False
        from threading import Thread
        def RunDSSinstance():
            global BokehSessionID
            global InstanceCreated
            DSS = dssInstance.OpenDSS(PlotOptions=PO, ResultOptions=RO, SimulationSettings=SS, LoggerOptions=LO)
            BokehSessionID = DSS.BokehSessionID
            InstanceCreated = True
            DSS.RunSimulation()
            pass

        self.dssInstanceThread = Thread(target=RunDSSinstance, args=[])
        self.timer.start()
        self.dssInstanceThread.start()

        while not InstanceCreated:
            import time
            time.sleep(0.2)

        url = 'http://localhost:5006/?bokeh-session-id=' + BokehSessionID
        self.ui.WebViewer.load(QUrl(url))
        self.ui.WebViewer.show()

        return


    def TimeLapsed(self):
        try:
            if not self.dssInstanceThread.isAlive():
                self.timer.stop()
            self.timer.setInterval(500)
            self.ui.textBrowser_Log.clear()
            Path = os.path.join(self.dssPath,  self.ActiveProject + '_' + self.ActiveScenario + '.log')
            with open(Path, "r") as myfile:
                Lines = myfile.readlines()
                myfile.close()
            for Line in Lines:
                self.ui.textBrowser_Log.append(Line.replace('\n', ''))
        except:
            pass

    def GetSimulationType(self):
        Type = str(self.ui.comboBox_SimType.currentText())
        if Type == 'Quasi static time series':
            return 'Daily'
        elif Type == 'Snapshot':
            return 'Snapshot'
        return

    def GetLoggingLevel(self):
        Type = str(self.ui.comboBox_LogLvl.currentText())
        if Type == 'WARNING':
            return logging.WARNING
        elif Type == 'INFO':
            return logging.INFO
        else:
            return logging.DEBUG

    def GetMainDSSfile(self, index):
        self.MainDSSfile = index.data()
        return

    def GetActiveProjectandScenario(self, index):
        self.ActiveProject = index.parent().data()
        if self.ActiveProject:
            self.ActiveScenario = index.data()
            ProjPath = os.path.join(self.dssPath,'ProjectFiles',self.ActiveProject)
            DSSFiles = self.GetFilesList(os.path.join(ProjPath, 'DSSfiles'), '.dss')
            ExportFiles = self.GetFilesList(
                os.path.join(ProjPath, 'PyDSS Settings', self.ActiveScenario, 'ExportLists'), '.xlsx')
            CtrlFiles = self.GetFilesList(
                os.path.join(ProjPath, 'PyDSS Settings', self.ActiveScenario, 'pyControllerList'), '.xlsx')
            PlotsFiles = self.GetFilesList(
                os.path.join(ProjPath, 'PyDSS Settings', self.ActiveScenario, 'pyPlotList'), '.xlsx')

            self.ui.listWidget_opendssfiles.clear()
            for dssFile in DSSFiles:
                item = QListWidgetItem(dssFile)
                self.ui.listWidget_opendssfiles.addItem(item)

            self.ui.listWidget_ExpFiles.clear()
            for ExpFile in ExportFiles:
                item = QListWidgetItem(ExpFile)
                self.ui.listWidget_ExpFiles.addItem(item)
            self.ui.listWidget_ExpFiles.clicked.connect(self.LoadExpTable)

            self.ui.listWidget_CtrlFiles.clear()
            for ctrlFile in CtrlFiles:
                item = QListWidgetItem(ctrlFile)
                self.ui.listWidget_CtrlFiles.addItem(item)
            self.ui.listWidget_CtrlFiles.clicked.connect(self.LoadCtrlTable)

            self.ui.listWidget_PltFiles.clear()
            for PltFile in PlotsFiles:
                item = QListWidgetItem(PltFile)
                self.ui.listWidget_PltFiles.addItem(item)
            self.ui.listWidget_PltFiles.clicked.connect(self.LoadPltTable)
        return

    def LoadExpTable(self, index):
        FileName = index.data()
        Data, r ,c = self.ReadExcelFile(os.path.join(self.dssPath,'ProjectFiles',self.ActiveProject, 'PyDSS Settings',
                                              self.ActiveScenario, 'ExportLists', FileName))
        self.ui.tableWidget_ExpTable.setRowCount(r)
        self.ui.tableWidget_ExpTable.setColumnCount(c)
        for i in range(r):
            for j in range(c):
                if i == 1 or j == 0:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Bold)
                else:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Normal)
                Text = QTableWidgetItem(str(Data[i][j]))
                Text.setFont(newfont)
                self.ui.tableWidget_ExpTable.setItem(i, j, Text)
        return

    def LoadCtrlTable(self, index):
        FileName = index.data()
        Data, r ,c = self.ReadExcelFile(os.path.join(self.dssPath,'ProjectFiles',self.ActiveProject, 'PyDSS Settings',
                                              self.ActiveScenario, 'pyControllerList', FileName))
        self.ui.tableWidget_CtrlTable.setRowCount(r)
        self.ui.tableWidget_CtrlTable.setColumnCount(c)
        for i in range(r):
            for j in range(c):
                if i == 1 or j == 0:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Bold)
                else:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Normal)
                Text = QTableWidgetItem(str(Data[i][j]))
                Text.setFont(newfont)
                self.ui.tableWidget_CtrlTable.setItem(i, j, Text)
        return

    def LoadPltTable(self, index):
        FileName = index.data()
        Data, r ,c = self.ReadExcelFile(os.path.join(self.dssPath,'ProjectFiles',self.ActiveProject, 'PyDSS Settings',
                                              self.ActiveScenario, 'pyPlotList', FileName))
        self.ui.tableWidget_PltTable.setRowCount(r)
        self.ui.tableWidget_PltTable.setColumnCount(c)

        for i in range(r):
            for j in range(c):
                if i == 1 or j == 0:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Bold)
                else:
                    newfont = QtGui.QFont("Times New Roman", 8, QtGui.QFont.Normal)
                Text = QTableWidgetItem(str(Data[i][j]))
                Text.setFont(newfont)
                self.ui.tableWidget_PltTable.setItem(i, j, Text)
        return

    def ReadExcelFile(self, FileName):
        import xlrd
        book = xlrd.open_workbook(FileName)
        sheet = book.sheet_by_index(0)
        data = []  # make a data store
        for i in range(sheet.nrows):
            data.append(sheet.row_values(i))  # drop all the values in the rows into data
        return data ,sheet.nrows , sheet.ncols

    def GetFilesList(self, Path , ext):
        FileList = []
        for file in os.listdir(Path):
            if file.endswith(ext):
                FileList.append(file)

        return FileList

    def PopulateProjectsList(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['PyDSS Projects'])
        self.ui.treeView_ProjectBrowser.setModel(model)

        self.Projects = os.listdir(os.path.join(self.dssPath,'ProjectFiles'))
        if 'desktop.ini' in self.Projects:
            self.Projects.remove('desktop.ini')
        for Proj in self.Projects:
            ProjectItem = QStandardItem(Proj)
            ProjectItem.setEditable(False)
            Scenarios = os.listdir(os.path.join(self.dssPath,'ProjectFiles',Proj,'PyDSS Settings'))
            if 'desktop.ini' in Scenarios:
                Scenarios.remove('desktop.ini')
            for Scenario in Scenarios:
                ScenarioItem = QStandardItem(Scenario)
                ScenarioItem.setEditable(False)
                ProjectItem.appendRow(ScenarioItem)
            model.appendRow(ProjectItem)
        self.ui.treeView_ProjectBrowser.clicked.connect(self.GetActiveProjectandScenario)

        Pymodel = QStandardItemModel()
        Pymodel.setHorizontalHeaderLabels(['Python files'])
        self.ui.treeView_PythonFiles.setModel(Pymodel)
        PythonFolders = ['pyControllers', 'PyPlots']
        for Folder in PythonFolders:
            ProjectItem = QStandardItem(Folder)
            ProjectItem.setEditable(False)
            Scenarios = self.GetFilesList(os.path.join(self.dssPath, Folder), '.py')
            for Scenario in Scenarios:
                ScenarioItem = QStandardItem(Scenario)
                ScenarioItem.setEditable(False)
                ScenarioItem.setEditable(False)
                ProjectItem.appendRow(ScenarioItem)
            Pymodel.appendRow(ProjectItem)
        self.ui.treeView_PythonFiles.clicked.connect(self.ReadPyFile)

        ResModel = QStandardItemModel()
        ResModel.setHorizontalHeaderLabels(['Result files'])
        self.ui.treeView_Results.setModel(ResModel)
        ResultFolder = os.listdir(os.path.join(self.dssPath, 'Export'))
        if 'desktop.ini' in ResultFolder:
            ResultFolder.remove('desktop.ini')
        for Folder in ResultFolder:
            ProjectItem = QStandardItem(Folder)
            ProjectItem.setEditable(False)
            Scenarios = os.listdir(os.path.join(self.dssPath, 'Export', Folder))
            for Scenario in Scenarios:
                if '.' not in Scenario:
                    ScenarioItem = QStandardItem(Scenario)
                    ScenarioItem.setEditable(False)
                    Files = self.GetFilesList(os.path.join(self.dssPath, 'Export', Folder, Scenario), '.csv')
                    for file in Files:
                        CSVItem = QStandardItem(file)
                        CSVItem.setEditable(False)
                        ScenarioItem.appendRow(CSVItem)
                    ProjectItem.appendRow(ScenarioItem)
            ResModel.appendRow(ProjectItem)
        self.ui.treeView_Results.clicked.connect(self.ReadResultHeaders)
        return

    def ReadResultHeaders(self, Index):
        self.ui.textEdit_Python.clear()
        FolderName = Index.parent().parent().data()
        if FolderName:
            ScenarioName = Index.parent().data()
            self.ResultFileName = Index.data()
            Path = os.path.join(self.dssPath,'Export', FolderName, ScenarioName, self.ResultFileName)
            self.MyResults = pd.read_csv(Path, sep = ',')
            Headers = list(self.MyResults.columns)
            self.ui.listWidget_Results.clear()
            for ElmName in Headers:
                item = QListWidgetItem(ElmName)
                item.setCheckState(Qt.Unchecked)
                self.ui.listWidget_Results.addItem(item)
            self.ui.listWidget_Results.clicked.connect(self.UpdateMLPplot)
        return

    def UpdateMLPplot(self, Index):
        self.MLPplot.ClearPlot()
        for index in range(self.ui.listWidget_Results.count()):
            Item  = self.ui.listWidget_Results.item(index)
            if Item.checkState() == Qt.Checked:
                ItemIndex = self.ui.listWidget_Results.indexFromItem(Item)
                self.MLPplot.plot(self.MyResults[ItemIndex.data()] , self.ResultFileName)

    def ReadPyFile(self, Index):
        self.ui.textEdit_Python.clear()
        FolderName = Index.parent().data()
        if FolderName:
            FileName = Index.data()
            Path = os.path.join(self.dssPath,FolderName,FileName)
            with open(Path, "r") as myfile:
                Lines = myfile.readlines()
                myfile.close()
            for Line in Lines:
                self.ui.textEdit_Python.append(Line.replace('\n',''))

    def Show(self):
        self.window.show()

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.subplots_adjust(left=.1, bottom=.1, right=.99, top=.90)
        self.axes = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        self.toolbar = NavigationToolbar(self, self)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


    def plot(self, data, FileName):
        ax = self.figure.add_subplot(111)
        ax.plot(data)
        ax.set_xlabel('Time steps', fontdict=font)
        ax.set_ylabel(FileName.replace('.csv', ''), fontdict=font)
        ax.legend(loc = 'upper right', fontsize=8)
        ax.grid(True)
        self.draw()

    def ClearPlot(self):
        self.axes.clear()

BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
app = QApplication(sys.argv)
PyDSSinstance = PyDSS()
PyDSSinstance.Show()
sys.exit(app.exec_())
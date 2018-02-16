from bokeh.plotting import figure, curdoc
from bokeh.io import output_file, save
from bokeh.models import ColumnDataSource, HoverTool, BoxSelectTool, PanTool, WheelZoomTool, \
    GMapPlot, GMapOptions, Range1d, MultiLine, Square, Circle, Triangle
from bokeh.client import push_session
import pandas as pd
import numpy as np
import pyproj


class Plot:
    Vmin = 0.95
    Vmax = 1.05
    Imin = 0
    Imax = 100
    VoltagePhase = 0
    CurrentPhase = 0
    def __init__(self,PlotProperties,dssBuses,dssObjectsByClass,dssCircuit):
        self.__dssBuses = dssBuses
        self.__PlotProperties = PlotProperties
        self.__dssObjectsByClass = dssObjectsByClass

        if PlotProperties['Projection']:
            self.__source_proj = pyproj.Proj("+init=EPSG:2784")# + PlotProperties['Project from'])
            self.__target_proj = pyproj.Proj("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
            self.__meter_factor = 0.3048006096012192

        BusProperty = list(dssBuses)[0]
        busProperties = dssBuses[BusProperty].GetVariableNames()
        newbusProperties = []
        for busProperty in busProperties:
            if dssBuses[BusProperty].DataLength(busProperty)[1] == 'Number':
                newbusProperties.append(busProperty)
            if dssBuses[BusProperty].DataLength(busProperty)[1] == 'List':
                t =  dssBuses[BusProperty].GetVariable(busProperty)[0]
                if isinstance(t,float):
                    newbusProperties.append(busProperty)
        # output to static HTML file

        self.LineData = self.GetLineData()
        self.BusData = self.GetBusData()

        if PlotProperties['Projection']:
            self.BusData['X'], self.BusData['Y'] = self.__transform(self.BusData['X'].tolist(),
                                                                    self.BusData['Y'].tolist())
        self.ResourceXYbyClass = self.GetResourceData()
        self.busDataSource = ColumnDataSource(self.BusData)

        ##########################     TOOL TIP DATA    ################################
        hoverBus = HoverTool(tooltips=[
            ("Name", "@Name"),
            ("(x,y)", "(@X, @Y)"),
            ("Voltage", "@puVoltage"),
        ])

        ##########################     Figure creation     ################################
        doc = curdoc()

        map_options = GMapOptions(lat=PlotProperties['Longitude'], lng=PlotProperties['Latitute'],
                                  map_type=PlotProperties['MapType'], zoom=PlotProperties['Zoom level'])
        self.__Figure = GMapPlot(x_range=Range1d(), y_range=Range1d(), map_options=map_options)
        self.__Figure.api_key = PlotProperties['Google Key']

        self.LineDataSource = ColumnDataSource(self.LineDict)
        self.Lineplot = MultiLine(xs="x", ys="y", line_color='green')
        self.__Figure.add_glyph(self.LineDataSource, self.Lineplot)

        self.BusPlot = Circle(x='X', y='Y', fill_color="blue", fill_alpha=0.8, line_color=None)
        self.__Figure.add_glyph(self.busDataSource, self.BusPlot)

        self.PlotElementClass('Transformers', 'black', 'circle')
        self.PlotElementClass('PVsystems', 'yellow', 'square')
        self.PlotElementClass('Loads', 'red', 'triangle')

        self.__Figure.add_tools(PanTool(), WheelZoomTool(), BoxSelectTool())

        output_file(PlotProperties['FileName'])

        doc.add_root(self.__Figure)
        doc.title = "PyDSS"

        session = push_session(doc)
        session.show(self.__Figure)  # open the document in a browser

        return

    def __transform(self, X, Y):
        Xt = []
        Yt = []
        if isinstance(X, list) and isinstance(X, list):
            for x1, y1 in zip(X, Y):
                Ans = pyproj.transform(self.__source_proj, self.__target_proj, float(x1) * self.__meter_factor,
                                       float(y1) * self.__meter_factor)
                #print(x1, y1, ' - ', Ans[0], Ans[1])
                Xt.append(Ans[0])
                Yt.append(Ans[1])
        else:
            Xt, Yt= pyproj.transform(self.__source_proj, self.__target_proj, float(X) * self.__meter_factor,
                                       float(Y) * self.__meter_factor)

        return Xt, Yt

    def UpdatePlot(self):

        return


    def PlotElementClass(self, Class, Color, Shape):
        X = self.ResourceXYbyClass[Class][0]
        Y = self.ResourceXYbyClass[Class][1]

        if self.__PlotProperties['Projection']:
            X, Y = self.__transform(X,Y)

        DataSource = ColumnDataSource({ 'X' : X ,'Y' : Y})
        Scatter = None
        if Shape=='square':
            Scatter = Square(x='X', y='Y', fill_color=Color, fill_alpha=0.8, line_color=None)
        elif Shape=='circle':
            Scatter = Circle(x='X', y='Y', fill_color=Color, fill_alpha=0.8, line_color=None)
        elif Shape=='triangle':
            Scatter = Triangle(x='X', y='Y', fill_color=Color, fill_alpha=0.8, line_color=None)
        self.__Figure.add_glyph(DataSource, Scatter)

    def GetResourceData(self):
        ResourceXYbyClass = {}
        for ObjectClass in self.__dssObjectsByClass.keys():
            if self.__dssObjectsByClass[ObjectClass] and ObjectClass != 'Circuits':
                ResourceXYbyClass[ObjectClass] = [[], [], [], [], []]
                for dssObject in self.__dssObjectsByClass[ObjectClass]:
                    Object = self.__dssObjectsByClass[ObjectClass][dssObject]
                    if Object.BusCount == 1:
                        BusName = Object.Bus[0].split('.')[0]
                        X, Y = self.__dssBuses[BusName].XY
                        if X != 0 and Y != 0:
                            ResourceXYbyClass[ObjectClass][0].append(X)
                            ResourceXYbyClass[ObjectClass][1].append(Y)
                            ResourceXYbyClass[ObjectClass][2].append(Y)
                    if Object.BusCount == 2:
                        BusName1 = Object.Bus[0].split('.')[0]
                        BusName2 = Object.Bus[1].split('.')[0]
                        X1, Y1 = self.__dssBuses[BusName1].XY
                        X2, Y2 = self.__dssBuses[BusName2].XY
                        if (X1 != 0 and Y1 != 0) and (X2 == 0 and Y2 == 0):
                            ResourceXYbyClass[ObjectClass][0].append(X1)
                            ResourceXYbyClass[ObjectClass][1].append(Y1)
                        elif (X1 == 0 and Y1 == 0) and (X2 != 0 and Y2 != 0):
                            ResourceXYbyClass[ObjectClass][0].append(X2)
                            ResourceXYbyClass[ObjectClass][1].append(Y2)
                        elif (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
                            ResourceXYbyClass[ObjectClass][0].append((X1 + X2) / 2)
                            ResourceXYbyClass[ObjectClass][1].append((Y1 + Y2) / 2)

        return ResourceXYbyClass

    def GetBusData(self):
        busX = []
        busY = []
        busNames = []
        busVoltage = []
        for dssBus in self.__dssBuses.keys():
            XY = self.__dssBuses[dssBus].XY
            if XY[0] != 0 and XY[1] != 0:
                busNames.append(dssBus)
                busX.append(float(XY[0]))
                busY.append(float(XY[1]))
                busVoltage.append(float(self.__dssBuses[dssBus].GetVariable('puVmagAngle')[2 * self.VoltagePhase]))

        BusData = pd.DataFrame(np.transpose([busNames, busX, busY, busVoltage]),
                               columns=['Name', 'X', 'Y', 'puVoltage'])
        return BusData

    def GetLineData(self):
        LineX = []
        LineY = []
        LineName = []
        LineCurrent = []
        Lines = self.__dssObjectsByClass['Lines']
        for name, Line in Lines.items():
            Bus1, Bus2 = Line.Bus
            X1, Y1 = self.__dssBuses[Bus1.split('.')[0]].XY
            X2, Y2 = self.__dssBuses[Bus2.split('.')[0]].XY
            if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
                if self.__PlotProperties['Projection']:
                    X1, Y1 = self.__transform(X1, Y1)
                    X2, Y2 = self.__transform(X2, Y2)
                LineX.append([float(X1), float(X2)])
                LineY.append([float(Y1), float(Y2)])
                LineName.append(name)
                LineCurrent.append(float(Line.GetVariable('CurrentsMagAng')[2 * self.CurrentPhase]))

        self.LineDict = {
            'x': LineX,
            'y': LineY,
        }

        LineData = pd.DataFrame(np.transpose([LineName, LineCurrent]),
                                     columns=['Name', 'Current'])
        return LineData

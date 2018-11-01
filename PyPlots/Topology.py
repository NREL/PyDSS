from bokeh.plotting import figure, curdoc
from bokeh.io import output_file
from bokeh.models import ColumnDataSource, ColorBar, \
    LinearColorMapper, HoverTool, BoxSelectTool, BoxZoomTool, \
    PanTool, WheelZoomTool, ResetTool, SaveTool, Label
from bokeh.palettes import Viridis, Plasma
from bokeh.client import push_session
import pandas as pd
import numpy as np

class Topology:
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

        output_file(PlotProperties['FileName'])
        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                               plot_height=self.__PlotProperties['Height'],
                               tools=[ResetTool(), hoverBus, BoxSelectTool(), SaveTool(),
                                      BoxZoomTool(), WheelZoomTool(), PanTool()])  # tools=[hover]

        self.__Figure.xgrid.grid_line_color = None
        self.__Figure.ygrid.grid_line_color = None
        self.__Figure.axis.visible = False

        self.VoltageColorPallete= Viridis[256]
        self.CurrentColorPallete= Plasma[256][200::-1]

        VoltageColor = self.GetColorArray(self.BusData['puVoltage'].astype(float), self.VoltageColorPallete, 'Voltage')
        CurrentColor = self.GetColorArray(self.LineData['Current'].astype(float), self.CurrentColorPallete, 'Current')
        mapperVolatge = LinearColorMapper(palette=self.VoltageColorPallete, low=self.Vmin, high=self.Vmax)
        mapperCurrent = LinearColorMapper(palette=self.CurrentColorPallete, low=self.Imin, high=self.Imax)
        ## PLOTS
        self.Lineplot = self.__Figure.multi_line(self.LineX, self.LineY, color=CurrentColor, legend='Lines')
        self.BusPlot = self.__Figure.circle(x='X', y='Y', source=self.busDataSource, color=VoltageColor, legend='Bus', size=5)

        self.PlotElementClass('Loads', 'red', 'triangle')
        self.PlotElementClass('PVsystems', 'darkorchid', 'square')
        self.PlotElementClass('Transformers', 'brown', 'circle')

        self.__Figure.legend.location = "top_left"
        self.__Figure.legend.click_policy = "hide"

        self.Voltage_color_bar = ColorBar(color_mapper=mapperVolatge, location=(0, 0),
                                     height=int(self.__PlotProperties['Height'] / 2) - 50)
        LABEL1 = Label(x=0, y=630, x_units='screen', y_units='screen',
                       text='Voltage [p.u.]', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle=3.142 / 2)

        LABEL2 = Label(x=0, y=200, x_units='screen', y_units='screen',
                       text='Current [Amp]', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle=3.142 / 2)

        self.Current_color_bar = ColorBar(color_mapper=mapperCurrent,
                                     location=(67, -int(self.__PlotProperties['Height'] / 2)),
                                     height=int(self.__PlotProperties['Height'] / 2) - 50)

        self.__Figure.add_layout(self.Voltage_color_bar, 'left')
        self.__Figure.add_layout(self.Current_color_bar, 'left')
        self.__Figure.add_layout(LABEL1)
        self.__Figure.add_layout(LABEL2)

        doc.add_root(self.__Figure)
        doc.title = "PyDSS"

        session = push_session(doc)
        session.show(self.__Figure)  # open the document in a browser

        return


    def UpdatePlot(self):

        self.LineData = self.GetLineData()
        self.BusData = self.GetBusData()
        self.busDataSource.data['puVoltage'] = self.BusData['puVoltage']
        VoltageColors = self.GetColorArray(self.BusData['puVoltage'].astype(float), self.VoltageColorPallete, 'Voltage')
        self.BusPlot.data_source.data['fill_color']= VoltageColors
        self.BusPlot.data_source.data['line_color'] = VoltageColors

        CurrentColor = self.GetColorArray(self.LineData['Current'].astype(float), self.CurrentColorPallete, 'Current')
        self.Lineplot.data_source.data['fill_color'] = CurrentColor
        self.Lineplot.data_source.data['line_color'] = CurrentColor

        self.Voltage_color_bar.color_mapper.low = self.Vmin
        self.Voltage_color_bar.color_mapper.high = self.Vmax
        self.Current_color_bar.color_mapper.low = self.Imin
        self.Current_color_bar.color_mapper.high = self.Imax

        return

    def GetColorArray(self, DataSeries, Pallete, Type):
        nBins = len(Pallete)
        if Type == 'Voltage':
            bins = np.arange(self.Vmin, self.Vmax, (self.Vmax-self.Vmin)/(nBins+1))
        else:
            bins = np.arange(self.Imin, self.Imax, (self.Imax-self.Imin)/(nBins+1))

        nBinEdges = len(bins)
        if nBinEdges - nBins > 1:
            bins = bins[:nBins+1]

        ColorArray = pd.cut(DataSeries, bins, labels=Pallete)
        ColorArray = ColorArray.replace(np.nan, Pallete[-1], regex=True)
        return ColorArray.tolist()

    def PlotElementClass(self, Class, Color, Shape):
        X = self.ResourceXYbyClass[Class][0]
        Y = self.ResourceXYbyClass[Class][1]
        if Shape=='square':
            self.__Figure.square(X, Y, color=Color, alpha=1, legend=Class)
        elif Shape=='circle':
            self.__Figure.circle(X, Y, color=Color, alpha=1, legend=Class)
        elif Shape=='triangle':
            self.__Figure.triangle(X, Y, color=Color, alpha=1, legend=Class)

    def GetResourceData(self):
        ResourceXYbyClass = {}
        for ObjectClass in self.__dssObjectsByClass.keys():
            if self.__dssObjectsByClass[ObjectClass]:
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
        self.LineX = []
        self.LineY = []
        LineName = []
        LineCurrent = []
        Lines = self.__dssObjectsByClass['Lines']
        for name, Line in Lines.items():
            Bus1, Bus2 = Line.Bus
            X1, Y1 = self.__dssBuses[Bus1.split('.')[0]].XY
            X2, Y2 = self.__dssBuses[Bus2.split('.')[0]].XY
            if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
                self.LineX.append([float(X1), float(X2)])
                self.LineY.append([float(Y1), float(Y2)])
                LineName.append(name)
                LineCurrent.append(float(Line.GetVariable('CurrentsMagAng')[2 * self.CurrentPhase]))

        LineData = pd.DataFrame(np.transpose([LineName, LineCurrent]),
                                     columns=['Name', 'Current'])
        return LineData

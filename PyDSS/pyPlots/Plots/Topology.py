
from  PyDSS.pyPlots.pyPlotAbstract import PlotAbstract

from bokeh.models import ColumnDataSource, ColorBar, \
    LinearColorMapper, HoverTool, BoxSelectTool, BoxZoomTool, \
    PanTool, WheelZoomTool, ResetTool, SaveTool, Label
from bokeh.palettes import Viridis, Plasma
from bokeh.plotting import figure
import pandas as pd
import numpy as np


class Topology(PlotAbstract):
    def __init__(self,PlotProperties,dssBuses,dssObjectsByClass,dssCircuit,dssSolver):
        super(Topology).__init__()

        self.__dssBuses = dssBuses
        self.__dssCircuit = dssCircuit
        self.__PlotProperties = PlotProperties
        self.__dssObjectsByClass = dssObjectsByClass

        # output to static HTML file

        self.LineX, self.LineY, self.Power = self.create_topology()
        self.Power = np.array(self.Power)
        # self.LineData = self.GetLineDataFrame()
        self.Pmin = self.Power.min()
        self.Pmax = self.Power.max()
        self.BusData = self.GetBusDataFrame()
        self.Vmin = self.BusData['puVoltage'].min()
        self.Vmax = self.BusData['puVoltage'].max()
        self.ResourceXYbyClass = self.GetResourceData()

        self.VoltageColorPallete = Viridis[256]
        self.CurrentColorPallete = Plasma[256]

        VoltageColor = self.GetColorArray(self.BusData['puVoltage'], self.VoltageColorPallete)
        CurrentColor = self.GetColorArray(self.Power, self.CurrentColorPallete)
        mapperVolatge = LinearColorMapper(palette=self.VoltageColorPallete, low=self.Vmin, high=self.Vmax)
        mapperCurrent = LinearColorMapper(palette=self.CurrentColorPallete, low=self.Pmin, high=self.Pmax)

        self.lineDataSource = ColumnDataSource({
            'Xs': self.LineX,
            'Ys': self.LineY,
            'LC': CurrentColor,
        })

        self.BusData['NodeColor'] = VoltageColor
        self.busDataSource = ColumnDataSource(self.BusData)

        ##########################     TOOL TIP DATA    ################################
        hoverBus = HoverTool(tooltips=[
            ("Name", "@Name"),
            ("(x,y)", "(@X, @Y)"),
            ("Voltage", "@puVoltage"),
        ])

        ##########################     Figure creation     ################################
        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                               plot_height=self.__PlotProperties['Height'],
                               tools=[ResetTool(), hoverBus, BoxSelectTool(), SaveTool(),
                                      BoxZoomTool(), WheelZoomTool(), PanTool()])  # tools=[hover]

        self.__Figure.xgrid.grid_line_color = None
        self.__Figure.ygrid.grid_line_color = None
        self.__Figure.axis.visible = False

        ## PLOTS
        self.Lineplot = self.__Figure.multi_line(xs='Xs', ys='Ys', color='LC', source=self.lineDataSource, legend='Lines')
        self.BusPlot = self.__Figure.circle(x='X', y='Y', color='NodeColor', source=self.busDataSource, legend='Bus', size=5)

        # self.PlotElementClass('Loads', 'red', 'triangle')
        # self.PlotElementClass('PVSystems', 'darkorchid', 'square')
        # self.PlotElementClass('Transformers', 'brown', 'circle')

        self.__Figure.legend.location = "top_left"
        self.__Figure.legend.click_policy = "hide"

        self.Voltage_color_bar = ColorBar(color_mapper=mapperVolatge, location=(0, 0),
                                     height=int(self.__PlotProperties['Height'] / 2) - 50)

        self.Current_color_bar = ColorBar(color_mapper=mapperCurrent,
                                          location=(0, 0),
                                          height=int(self.__PlotProperties['Height'] / 2) - 50)

        LABEL1 = Label(x=0, y=630, x_units='screen', y_units='screen',
                       text='Voltage [p.u.]', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle=3.142 / 2)

        LABEL2 = Label(x=0, y=200, x_units='screen', y_units='screen',
                       text='Current [Amp]', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle=3.142 / 2)


        # self.__Figure.add_layout(LABEL1)
        # self.__Figure.add_layout(LABEL2)
        self.__Figure.add_layout(self.Voltage_color_bar, 'left')
        self.__Figure.add_layout(self.Current_color_bar, 'left')
        return

    def GetFigure(self):
        return self.__Figure

    def UpdatePlot(self):

        self.LineX, self.LineY, self.Power = self.create_topology()
        self.Power = np.array(self.Power)
        # self.LineData = self.GetLineDataFrame()
        self.Pmin = self.Power.min()
        self.Pmax = self.Power.max()
        self.BusData = self.GetBusDataFrame()
        self.Vmin = self.BusData['puVoltage'].min()
        self.Vmax = self.BusData['puVoltage'].max()

        VoltageColor = self.GetColorArray(self.BusData['puVoltage'], self.VoltageColorPallete)
        CurrentColor = self.GetColorArray(self.Power, self.CurrentColorPallete)
        VoltageColor = ['#ffffff' if v == np.NaN else v for v in VoltageColor]
        CurrentColor = ['#ffffff' if v == np.NaN else v for v in CurrentColor]

        self.BusPlot.data_source.data['puVoltage'] = self.BusData['puVoltage']
        self.BusPlot.data_source.data['NodeColor']= VoltageColor

        self.Lineplot.data_source.data['LC'] = CurrentColor

        self.Voltage_color_bar.color_mapper.low = self.Vmin
        self.Voltage_color_bar.color_mapper.high = self.Vmax
        self.Current_color_bar.color_mapper.low = self.Pmin
        self.Current_color_bar.color_mapper.high = self.Pmax
        return

    def GetColorArray(self, DataSeries, Pallete):
        Pallete = list(set(Pallete))
        minVal = DataSeries.min()
        maxVal = DataSeries.max()
        nBins = len(Pallete)
        bins = np.arange(minVal - 1e-8, maxVal, (maxVal-minVal)/(nBins))
        ColorArray = pd.cut(DataSeries, bins, labels=Pallete)
        return ColorArray.tolist()

    def PlotElementClass(self, Class, Color, Shape):
       if Class in self.ResourceXYbyClass:
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
                    if hasattr(Object, 'BusCount'):
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

    def GetBusDataFrame(self):
        BusNames = self.__dssCircuit.AllNodeNames()
        BusNames =[B.split('.')[0] for B in BusNames]
        Vmag = self.__dssCircuit.AllBusMagPu()

        busX = []
        busY = []
        for dssBus in BusNames:
            dssBus = dssBus.split('.')[0]
            XY = self.__dssBuses[dssBus].XY
            #if XY[0] != 0 and XY[1] != 0:
            busX.append(float(XY[0]))
            busY.append(float(XY[1]))

        BusData = pd.DataFrame(np.transpose([BusNames, busX, busY, Vmag]),
                               columns=['Name', 'X', 'Y', 'puVoltage'])
        BusData['puVoltage'] = BusData['puVoltage'].astype(float)
        BusData['X'] = BusData['X'].astype(float)
        BusData['Y'] = BusData['Y'].astype(float)
        BusData = BusData[((BusData['X'] > 0) & (BusData['Y'] > 0)) & (BusData['puVoltage'] > 0)]
        BusData = BusData.sort_values('puVoltage').drop_duplicates(subset=['Name'], keep='last')
        return BusData

    def GetLineDataFrame(self):
        ElmNames = self.__dssCircuit.AllElementNames()
        Losses =self.__dssCircuit.AllElementLosses()
        Losses = np.abs(np.add(Losses[::2] , np.multiply(1j , Losses[1::2])))
        LineData = np.transpose([ElmNames, Losses]).T
        LineData = pd.DataFrame(LineData.T, columns=['Name', 'Loss'])
        LineData['Loss'] = LineData['Loss'].astype(float)
        return LineData

    def create_topology(self):
        LineX = []
        LineY = []
        Power = []
        Lines = self.__dssObjectsByClass['Lines']
        for name, Line in Lines.items():
            Bus1, Bus2 = Line.Bus
            X1, Y1 = self.__dssBuses[Bus1.split('.')[0]].XY
            X2, Y2 = self.__dssBuses[Bus2.split('.')[0]].XY
            if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
                LineX.append([float(X1), float(X2)])
                LineY.append([float(Y1), float(Y2)])
                Power.append(sum(Line.GetValue('Powers')[::2]))

        return LineX, LineY, Power

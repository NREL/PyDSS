
from bokeh.models.widgets import Button, RadioButtonGroup, Select, Slider
from bokeh.plotting import figure, output_file, show
from bokeh.io import output_file, show
from bokeh.layouts import widgetbox, gridplot
from bokeh.models import ColumnDataSource, ColorBar, LinearColorMapper , Label

class Plot:
    def __init__(self,PlotProperties,dssBuses,dssObjectsByClass):
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
        output_file(PlotProperties['FileName'])
        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                               plot_height=self.__PlotProperties['Height'])

        LABEL1 = Label(x=-50, y=300, x_units='screen', y_units='screen',
                       text='Label 1', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle= 3.142/2)

        LABEL2 = Label(x=30, y=300, x_units='screen', y_units='screen',

                       text='Label 2', render_mode='css',
                       background_fill_color='white', background_fill_alpha=1.0, angle= 3.142/2)

        self.__Figure.add_layout(LABEL1)
        self.__Figure.add_layout(LABEL2)

        self.busX = []
        self.busY = []
        ColorPpty = []
        for dssBus in dssBuses.keys():
            XY = dssBuses[dssBus].XY
            if XY[0] != 0 and XY[1] != 0:
                self.busX.append(XY[0])
                self.busY.append(XY[1])
                ColorPpty.append(max(dssBuses[dssBus].GetVariable('puVmagAngle')[0::2]))
        self.__Figure.circle(self.busX, self.busY, color=ColorPpty, alpha=100)

        Pallete = ["#023858", "#045a8d", "#0570b0", "#3690c0", "#74a9cf", "#a6bddb", "#d0d1e6", "#ece7f2", "#fff7fb"]
        mapper = LinearColorMapper(palette=Pallete, low=min(ColorPpty), high=max(ColorPpty))
        color_bar = ColorBar(color_mapper=mapper, location=(10, 0))
        color_bar1 = ColorBar(color_mapper=mapper, location=(0, 0))
        self.__Figure.add_layout(color_bar, 'left')
        self.__Figure.add_layout(color_bar1, 'left')

        self.LineX = []
        self.LineY = []
        Lines =  dssObjectsByClass['Lines']
        for name, Line in Lines.items():
            Bus1, Bus2 = Line.Bus
            X1, Y1 = dssBuses[Bus1.split('.')[0]].XY
            X2, Y2 = dssBuses[Bus2.split('.')[0]].XY
            if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
                self.LineX.append([X1,X2])
                self.LineY.append([Y1,Y2])
        self.__Figure.multi_line(self.LineX, self.LineY)

        self.ResourceXYbyClass = {}
        for ObjectClass in dssObjectsByClass.keys():
            if dssObjectsByClass[ObjectClass]:
                self.ResourceXYbyClass[ObjectClass] = [[],[]]
                for dssObject in dssObjectsByClass[ObjectClass]:
                    Object = dssObjectsByClass[ObjectClass][dssObject]
                    if Object.BusCount == 1:
                        BusName = Object.Bus[0].split('.')[0]
                        X,Y = dssBuses[BusName].XY
                        if X != 0 and Y != 0:
                            self.ResourceXYbyClass[ObjectClass][0].append(X)
                            self.ResourceXYbyClass[ObjectClass][1].append(Y)

        print (self.ResourceXYbyClass.keys())
        Class = 'Loads'  #
        X = self.ResourceXYbyClass[Class][0]
        Y = self.ResourceXYbyClass[Class][1]

        self.__Figure.triangle(X, Y, color='red', alpha=1)
        self.BusPropertySel = Select(title="Bus color property", value='asdsa' , options=newbusProperties)
        self.BusPropertySelVal = RadioButtonGroup(labels=['A', 'B', 'C', 'N','Min','Max','Avg'], active=0)
        self.LinePptySel = Select(title="Line color property", value='asdsa', options=newbusProperties)
        self.LinePptySelVal = RadioButtonGroup(labels=['A', 'B', 'C', 'N', 'Min', 'Max', 'Avg'], active=0)
        self.dssObjectTypeSel = Select(title="Element class:", value="foo", options=list(dssObjectsByClass))
        self.dssObjValueType = RadioButtonGroup(labels=['Properties', 'Variables'], active=0)
        self.dssObjValue = Select(title="Element class:", value="foo", options=list(dssObjectsByClass))

        self.UpdateButton = Button(label="Update")
        self.TimeRefreshSlider = Slider(start=0, end=10, value=1, step=.1, title="Refresh time - [s]")
        self.Grid = gridplot([widgetbox(self.BusPropertySel,
                                        self.BusPropertySelVal,
                                        self.LinePptySel,
                                        self.LinePptySelVal,
                                        self.dssObjectTypeSel,
                                        self.dssObjValueType,
                                        self.dssObjValue,
                                        self.UpdateButton,
                                        self.TimeRefreshSlider,
                                        width=300),
                              self.__Figure], ncols=2)
        # put the results in a row
        show(self.Grid)
        return

    def UpdatePlot(self):
        print ('YOLO')
        return

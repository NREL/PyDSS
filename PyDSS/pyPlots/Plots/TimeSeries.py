from  PyDSS.pyPlots.pyPlotAbstract import PlotAbstract
from bokeh.plotting import figure, curdoc
from bokeh.io import output_file
from bokeh.client import push_session
from bokeh.layouts import column
from bokeh.palettes import Set1
from ast import literal_eval as LE


class TimeSeries(PlotAbstract):
    def __init__(self,PlotProperties, dssBuses, dssObjects, dssCircuit, dssSolver):
        super(TimeSeries).__init__()
        self.__dssBuses = dssBuses
        self.__dssObjs = dssObjects
        self.__PlotProperties = PlotProperties
        self.__Properties =  LE(PlotProperties['Properties'])
        self.__index = LE(PlotProperties['index'])
        self.__multiplier = LE(PlotProperties['yScaler'])

        if self.__PlotProperties['yObjectType'] == 'Element':
            self.yObj = self.__dssObjs[self.__PlotProperties['yObjName']]
        elif self.__PlotProperties['yObjectType'] == 'Bus':
            self.yObj = self.__dssBuses[self.__PlotProperties['yObjName']]
        elif self.__PlotProperties['yObjectType'] == 'Circuit':
            self.yObj = dssCircuit

        self.Figures = []
        self.Y = [[] for x in self.__Properties]
        self.X = [[] for x in self.__Properties]
        self.Lines = [None for x in self.__Properties]
        output_file(PlotProperties['FileName'])
        for i, yProperties in enumerate(self.__Properties):
            Multiplier = self.__multiplier[i]
            pptyType ,Property = yProperties.split('.')
            if pptyType == 'p':
                newValue = self.yObj.GetParameter(Property)
            elif pptyType == 'v' and self.__PlotProperties['yObjectType'] != 'Circuit':
                newValue = self.yObj.GetVariable(Property)
            elif pptyType == 'v' and self.__PlotProperties['yObjectType'] == 'Circuit':
                newValue = getattr(self.yObj, Property)()

            if newValue is not None:
                if isinstance(newValue, list):
                    if self.__index[i] == 'SumEven':
                        self.Y[i].append(Multiplier * sum(newValue[::2]))
                    elif self.__index[i] == 'SumOdd':
                        self.Y[i].append(Multiplier * sum(newValue[1::2]))
                    elif self.__index[i] == 'Even' :
                        self.Y[i]= [[Multiplier * x] for x in newValue[::2]]
                    elif self.__index[i] == 'Odd':
                        self.Y[i] = [[Multiplier * x] for x in newValue[1::2]]
                    elif 'Index=' in self.__index[i]:
                        c = int(self.__index[i].replace('Index=', ''))
                        self.Y[i].append(Multiplier * newValue[c])
                else:
                    self.Y[i].append(Multiplier * newValue)
                self.X[i] = range(len(self.Y[i])+1)

            Figure = figure(plot_width=self.__PlotProperties['Width'],
                            plot_height=self.__PlotProperties['Height'],
                            title=self.__PlotProperties['yObjName'])
            if isinstance(self.Y[i][0], list):
                self.Lines[i] = []
                for j, Y in enumerate(self.Y[i]):
                    a = Figure.line(self.X[i], Y, line_width=3, line_alpha=1, color=Set1[9][j])
                    self.Lines[i].append(a)
            else:
                self.Lines[i] = Figure.line(self.X[i], self.Y[i], line_width=3, line_alpha=1)
            if self.__index[i] is not None:
                Figure.yaxis.axis_label = Property + '-' + self.__index[i]
            else:
                Figure.yaxis.axis_label = Property
            Figure.xaxis.axis_label = 'Timesteps'
            self.Figures.append(Figure)

        self.Layout = column(self.Figures)
        self.doc = curdoc()
        self.doc.add_root(self.Layout)
        self.doc.title = "PyDSS"
        self.session = push_session(self.doc)
        #self.session.show(self.Layout)  # open the document in a browser

        return

    def GetSessionID(self):
        return self.session.id

    def UpdatePlot(self):
        for i, yProperties in enumerate(self.__Properties):
            Multiplier = self.__multiplier[i]
            pptyType ,Property = yProperties.split('.')
            if pptyType == 'p':
                newValue = self.yObj.GetParameter(Property)
            elif pptyType == 'v' and self.__PlotProperties['yObjectType'] != 'Circuit':
                newValue = self.yObj.GetVariable(Property)
            elif pptyType == 'v' and self.__PlotProperties['yObjectType'] == 'Circuit':
                newValue = getattr(self.yObj, Property)()

            if newValue is not None:
                if isinstance(newValue, list):
                    if self.__index[i] == 'SumEven':
                        self.Y[i].append(Multiplier * sum(newValue[::2]))
                    elif self.__index[i] == 'SumOdd':
                        self.Y[i].append(Multiplier * sum(newValue[1::2]))
                    elif self.__index[i] == 'Even':
                        for j, Value in enumerate(newValue[::2]):
                            self.Y[i][j].append(Multiplier * Value)
                    elif self.__index[i] == 'Odd':
                        for j, Value in enumerate(newValue[1::2]):
                            self.Y[i][j].append(Multiplier * Value)
                    elif 'Index=' in self.__index[i]:
                        c = int(self.__index[i].replace('Index=',''))
                        self.Y[i].append(Multiplier * newValue[c])
                else:
                    self.Y[i].append(Multiplier * newValue)
                self.X[i] = range(len(self.Y[i])+1)

            if isinstance(self.Y[i][0], list):
                for j, Y in enumerate(self.Y[i]):
                    self.Lines[i][j].data_source.data['x'] = range(len(Y)+1)
                    self.Lines[i][j].data_source.data['y'] = Y
            else:
                if self.__PlotProperties['Dynamic'] and len(self.X[i]) > self.__PlotProperties['nSamples']:
                    self.X[i] = self.X[i][-self.__PlotProperties['nSamples']:]
                    self.Y[i] = self.Y[i][-self.__PlotProperties['nSamples']:]
                self.Lines[i].data_source.data['x'] = self.X[i]
                self.Lines[i].data_source.data['y'] = self.Y[i]
        return

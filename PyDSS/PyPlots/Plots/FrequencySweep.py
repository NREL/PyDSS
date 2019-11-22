
from  PyDSS.pyPlots.pyPlotAbstract import PlotAbstract
from bokeh.plotting import figure, curdoc
from bokeh.io import output_file
from bokeh.models import ColumnDataSource
from bokeh.client import push_session

class FrequencySweep(PlotAbstract):
    def __init__(self, PlotProperties, dssBuses, dssObjects, dssCircuit, dssSolver):
        super(FrequencySweep).__init__()
        self.__dssSolver = dssSolver
        self.__dssBuses = dssBuses
        self.__dssObjs = dssObjects
        self.__dssCircuit = dssCircuit
        self.__PlotProperties = PlotProperties
        self.plotted_object = self.getObject(PlotProperties['Object Name'], PlotProperties['Object Type'])

        output_file(PlotProperties['FileName'])
        freq = dssSolver.getFrequency()
        yVal = self.getObjectValue(self.plotted_object, PlotProperties['Property'], PlotProperties['Indices'])

        self.data = {'frequency': [0]}
        self.data[PlotProperties['Property']] = [0]
        self.data_source = ColumnDataSource(self.data)
        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                        plot_height=self.__PlotProperties['Height'],
                        title= 'Frequency sweep plot: ' + PlotProperties['Object Name'])

        self.ScatterPlot = self.__Figure.line(x= 'frequency', y= PlotProperties['Property'], color='green',
                                              source=self.data_source)
        self.__Figure.yaxis.axis_label = PlotProperties['Property'] + ' - ' + PlotProperties['Indices']
        self.__Figure.xaxis.axis_label = 'frequency [Hz]'
        self.doc = curdoc()
        self.doc.add_root(self.__Figure)
        self.doc.title = "PyDSS"
        self.session = push_session(self.doc)
        self.session.show(self.__Figure)  # open the document in a browser
        self.__time = dssSolver.GetDateTime()
        return


    def GetSessionID(self):
        return self.session.id

    def getObjectValue(self, Obj, ObjPpty, Index):
        pptyValue = Obj.GetVariable(ObjPpty)
        if pptyValue is not None:
            if isinstance(pptyValue, list):
                if Index == 'SumEven':
                    result = sum(pptyValue[::2])
                elif Index == 'SumOdd':
                    result = sum(pptyValue[1::2])
                elif Index == 'Even':
                    result =  pptyValue[::2]
                elif Index == 'Odd':
                    result = pptyValue[1::2]
                elif 'Index=' in Index:
                    c = int(Index.replace('Index=', ''))
                    result = pptyValue[c]
            else:
                result = pptyValue
        return result

    def getObject(self, ObjName, ObjType):
        if ObjType == 'Element':
            Obj = self.__dssObjs[ObjName]
        elif ObjType == 'Bus':
            Obj = self.__dssBuses[ObjName]
        elif ObjType == 'Circuit':
            Obj = self.__dssCircuit
        else:
            Obj = None
        return Obj


    def UpdatePlot(self):
        if self.__dssSolver.GetDateTime() != self.__time:
            #self.data_source.data = self.data
            self.data = {'frequency': [0]}
            self.data[self.__PlotProperties['Property']] = [0]
            self.__time = self.__dssSolver.GetDateTime()

        yVal = self.getObjectValue(self.plotted_object, self.__PlotProperties['Property'], self.__PlotProperties['Indices'])
        freq = self.__dssSolver.getFrequency()

        self.data[self.__PlotProperties['Property']].append(yVal)
        self.data['frequency'].append(freq)
        self.data_source.data = self.data

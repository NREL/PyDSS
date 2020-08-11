from  PyDSS.pyPlots.pyPlotAbstract import PlotAbstract
from bokeh.plotting import figure, curdoc
from bokeh.io import output_file
from bokeh.models import ColumnDataSource, ColorBar, \
    LinearColorMapper, HoverTool, BoxSelectTool, BoxZoomTool, \
    PanTool, WheelZoomTool, ResetTool, SaveTool, Label
from bokeh.palettes import Plasma
from bokeh.client import push_session
import pandas as pd
import numpy as np



class XY(PlotAbstract):
    def __init__(self,PlotProperties, dssBuses, dssObjects, dssCircuit, dssSolver):
        super(XY).__init__()

        self.__dssBuses = dssBuses
        self.__dssObjs = dssObjects
        self.__dssCircuit = dssCircuit
        self.__PlotProperties = PlotProperties

        self.xMul = PlotProperties['xScaler']
        self.yMul = PlotProperties['yScaler']
        self.cMul = PlotProperties['cScaler']

        self.xInd = PlotProperties['xindex']
        self.yInd = PlotProperties['yindex']
        self.cInd = PlotProperties['cindex']

        self.xObj = self.getObject(PlotProperties['xObjName'],PlotProperties['xObjectType'])
        self.yObj = self.getObject(PlotProperties['yObjName'],PlotProperties['yObjectType'])
        self.cObj = self.getObject(PlotProperties['cObjName'],PlotProperties['cObjectType'])

        output_file(PlotProperties['FileName'])

        xVal = self.getObjectValue(self.xObj, PlotProperties['xObjectType'], PlotProperties['xProperty'],
                                   self.xInd, self.xMul)
        yVal = self.getObjectValue(self.yObj, PlotProperties['yObjectType'], PlotProperties['yProperty'],
                                   self.yInd, self.yMul)
        cVal = self.getObjectValue(self.cObj, PlotProperties['cObjectType'], PlotProperties['cProperty'],
                                   self.cInd, self.cMul)

        self.xVals = [xVal]
        self.yVals = [yVal]
        self.cVals = [cVal]

        Data = pd.DataFrame(np.transpose([self.xVals, self.yVals, self.cVals]),
                               columns=['X', 'Y', 'C'])
        ColorArray = self.GetColorArray(Data['C'].astype(float), Plasma[256])

        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                        plot_height=self.__PlotProperties['Height'],
                        title= 'XY Plot: Color - ' + PlotProperties['cObjName'] + ' - ' + PlotProperties['cProperty'])

        self.ScatterPlot = self.__Figure.scatter(x= Data['X'], y=Data['Y'], fill_color=Plasma[256][1],
                                                 fill_alpha=0.6, line_color=None, size=7)

        self.__Figure.yaxis.axis_label = PlotProperties['yObjName'] + ' - ' + PlotProperties['yProperty']
        self.__Figure.xaxis.axis_label = PlotProperties['xObjName'] + ' - ' + PlotProperties['xProperty']

        self.doc = curdoc()
        self.doc.add_root(self.__Figure)
        self.doc.title = "PyDSS"
        self.session = push_session(self.doc)
        #self.session.show(self.__Figure)  # open the document in a browser
        return

    def GetSessionID(self):
        return self.session.id

    def GetColorArray(self, DataSeries, Pallete):
        if len(DataSeries)> 10:
            nBins = len(Pallete)
            minVal = min(DataSeries)
            maxVal = max(DataSeries)
            bins = np.arange(minVal, maxVal, (maxVal-minVal)/(nBins+1))

            nBinEdges = len(bins)
            if nBinEdges - nBins > 1:
                bins = bins[:nBins+1]

            ColorArray = pd.cut(DataSeries, bins, labels=Pallete)
            ColorArray = ColorArray.replace(np.nan, Pallete[-1], regex=True)
            ColorArray = ColorArray.tolist()
        else:
            ColorArray = Pallete[0]
        return ColorArray

    def getObjectValue(self, Obj, ObjType, ObjPpty, Index, Multiplier):
        pptyType, Property = ObjPpty.split('.')
        if pptyType == 'p':
            pptyValue = float(Obj.GetParameter(Property))
        elif pptyType == 'v' and ObjType != 'Circuit':
            pptyValue = Obj.GetVariable(Property)
        elif pptyType == 'v' and ObjType == 'Circuit':
            pptyValue = getattr(Obj, Property)()

        if pptyValue is not None:
            if isinstance(pptyValue, list):
                if Index.lower() == 'sumeven':
                    result = Multiplier * sum(pptyValue[::2])
                elif Index.lower() == 'sumodd':
                    result = Multiplier * sum(pptyValue[1::2])
                elif Index.lower() == 'even':
                    result = [[Multiplier * x] for x in pptyValue[::2]]
                elif Index.lower() == 'odd':
                    result = [[Multiplier * x] for x in pptyValue[1::2]]
                elif 'Index=' in Index:
                    c = int(Index.replace('Index=', ''))
                    result = Multiplier * pptyValue[c]
            else:
                result = Multiplier * pptyValue

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
        xVal = self.getObjectValue(self.xObj, self.__PlotProperties['xObjectType'], self.__PlotProperties['xProperty'],
                                   self.xInd, self.xMul)
        yVal = self.getObjectValue(self.yObj, self.__PlotProperties['yObjectType'], self.__PlotProperties['yProperty'],
                                   self.yInd, self.yMul)
        cVal = self.getObjectValue(self.cObj, self.__PlotProperties['cObjectType'], self.__PlotProperties['cProperty'],
                                   self.cInd, self.cMul)

        self.xVals.append(xVal)
        self.yVals.append(yVal)
        self.cVals.append(cVal)

        Data = pd.DataFrame(np.transpose([self.xVals, self.yVals, self.cVals]),
                               columns=['X', 'Y', 'C'])
        Data = Data.sort_values('X')
        Data = Data.drop_duplicates(subset=Data.columns)
        #ColorArray = self.GetColorArray(Data['X'].astype(float), Plasma[256])
        self.ScatterPlot.data_source.data['x'] = Data['X']
        self.ScatterPlot.data_source.data['y'] = Data['Y']
        #self.ScatterPlot
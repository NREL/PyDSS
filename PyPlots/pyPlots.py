import Topology
import SagPlot
import HeatMap
import TimeSeries
import XYPlot

PlotTypes ={
    'Network layout': Topology.Plot,
	'Sag plot': SagPlot.Plot,
	'Heat map': HeatMap.Plot,
	'Time series': TimeSeries.Plot,
	'Heat map': XYPlot.Plot,
}


def Create(PlotType, PlotPropertyDict, dssBuses, dssObjectsByClass):
    try:
        PlotObject = PlotTypes[PlotType](PlotPropertyDict,dssBuses,dssObjectsByClass)
    except:
        print 'The object dictionary does not contain ' + PlotType
        return -1
    return PlotObject


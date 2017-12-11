import Topology
import SagPlot
import HeatMap
import TimeSeries
import XYPlot

PlotTypes ={
    'Network layout' : Topology.Plot,
	'Sag plot'       : SagPlot.Plot,
	'Heat map'       : HeatMap.Plot,
	'Time series'    : TimeSeries.Plot,
	'XY plot'        : XYPlot.Plot,
}


def Create(PlotType, PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit):
    PlotObject = PlotTypes[PlotType](PlotPropertyDict, dssBuses, dssObjectsByClass, dssCircuit)
    # try:
    #
    # except:
    #     print ('The object dictionary does not contain ' + PlotType)
    #     return -1
    return PlotObject

defalultPO = {
        'Network layout': False,
        'Time series': False
    }
from  PyDSS.pyPlots.pyPlotAbstract import PlotAbstract
from bokeh.plotting import figure, curdoc
from bokeh.io import output_file
from bokeh.client import push_session
from bokeh.layouts import  column
from bokeh.palettes import Set1
from ast import literal_eval as LE
from bokeh.models import ColumnDataSource, ColorBar, \
    LinearColorMapper, HoverTool, BoxSelectTool, BoxZoomTool, \
    PanTool, WheelZoomTool, ResetTool, SaveTool, Label
import pandas as pd
import numpy as np
import math

class VoltageDistance(PlotAbstract):
	def __init__(self,PlotProperties, dssBuses, dssObjectsbyClass, dssCircuit, dssSolver):
		super(VoltageDistance).__init__()
		self.__dssBuses = dssBuses
		self.__PlotProperties = PlotProperties
		self.__dssObjectsByClass = dssObjectsbyClass

		self.VoltagePhase = PlotProperties['Phase']

		self.BusData = self.GetBusData()
		self.LineData = self.GetLineData()
		self.busDataSource = ColumnDataSource(self.BusData)
		Vlb = PlotProperties['Vlb']
		Vub = PlotProperties['Vub']
		##########################     TOOL TIP DATA    ################################
		hoverBus = HoverTool(tooltips=[
			("Name", "@Name"),
			("Distance", "@Distance"),
			("Voltage", "@puVoltage"),
		])

		output_file(PlotProperties['FileName'])
		self.__Figure = figure(plot_width=int(self.__PlotProperties['Width']),
							   plot_height=int(self.__PlotProperties['Height']),
							   tools=[ResetTool(), hoverBus, BoxSelectTool(), SaveTool(),
									  BoxZoomTool(), WheelZoomTool(), PanTool()])  # tools=[hover]
		a = self.BusData['Distance'].max()
		self.BusPlot = self.__Figure.circle(x='Distance', y='puVoltage', source=self.busDataSource, legend='Nodes')
		self.lineLB = self.__Figure.line([0, PlotProperties['Dmax']], [Vlb, Vlb], line_width=2)
		self.lineUB = self.__Figure.line([0, PlotProperties['Dmax']], [Vub, Vub], line_width=2)
		self.Lineplot = self.__Figure.multi_line(self.LineX, self.LineY, legend='Lines', color='green')
		self.Lineplot1 = self.__Figure.multi_line(self.trX, self.trY, legend='XFMRs', color='red')

		self.__Figure.legend.location = "top_right"
		self.__Figure.legend.click_policy = "hide"

		curdoc().add_root(self.__Figure)
		curdoc().title = "PyDSS"

		session = push_session(curdoc())
		session.show(self.__Figure)
		return


	def GetBusData(self):

		self.busNames = []
		busVoltage = []
		busDistance = []

		for dssBus in self.__dssBuses:
			if self.__PlotProperties['Voltage Level'] == 'All':
				self.busNames.append(dssBus)
				busDistance.append(float(self.__dssBuses[dssBus].Distance))
				busVoltage.append(float(self.__dssBuses[dssBus].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]))
			elif float(self.__PlotProperties['Voltage Level'])  == self.__dssBuses[dssBus].GetVariable('kVBase') * math.sqrt(3):
				self.busNames.append(dssBus)
				busDistance.append(float(self.__dssBuses[dssBus].Distance))
				busVoltage.append(float(self.__dssBuses[dssBus].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]))

		BusData = pd.DataFrame(np.transpose([self.busNames, busDistance, busVoltage]),
							   columns=['Name', 'Distance', 'puVoltage'])
		return BusData

	def GetLineData(self):
		self.LineX = []
		self.LineY = []

		self.trX = []
		self.trY = []
		LineName = []

		XFMRs = self.__dssObjectsByClass['Transformers']
		Lines = self.__dssObjectsByClass['Lines']


		for name, Line in Lines.items():
			Bus1, Bus2 = nBuses = Line.Bus
			Bus1 = Bus1.split('.')[0]
			Bus2 = Bus2.split('.')[0]
			if Bus1 in self.busNames or Bus2 in self.busNames:
				X1 = self.__dssBuses[Bus1].Distance
				Y1 = self.__dssBuses[Bus1].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]
				X2 = self.__dssBuses[Bus2].Distance
				Y2 = self.__dssBuses[Bus2].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]
				if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
					self.LineX.append([float(X1), float(X2)])
					self.LineY.append([float(Y1), float(Y2)])
					LineName.append(name)

		for name, Line in XFMRs.items():
			Bus1, Bus2 = nBuses = Line.Bus
			Bus1 = Bus1.split('.')[0]
			Bus2 = Bus2.split('.')[0]
			if Bus1 in self.busNames or Bus2 in self.busNames:
				X1 = self.__dssBuses[Bus1].Distance
				Y1 = self.__dssBuses[Bus1].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]
				X2 = self.__dssBuses[Bus2].Distance
				Y2 = self.__dssBuses[Bus2].GetVariable('puVmagAngle')[2 * int(self.VoltagePhase)]
				if (X1 != 0 and Y1 != 0) and (X2 != 0 and Y2 != 0):
					self.trX.append([float(X1), float(X2)])
					self.trY.append([float(Y1), float(Y2)])
					LineName.append(name)
		return 0

	def UpdatePlot(self):
		self.BusData = self.GetBusData()
		self.LineData = self.GetLineData()
		self.Lineplot.data_source.data['ys'] = self.LineY
		self.Lineplot1.data_source.data['ys'] = self.trY
		self.busDataSource.data['puVoltage'] = self.BusData['puVoltage']

		return 0
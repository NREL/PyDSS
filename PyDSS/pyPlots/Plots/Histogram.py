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


class Histogram(PlotAbstract):
	def __init__(self, PlotProperties, dssBuses, dssObjectsbyClass, dssCircuit, dssSolver):
		super(Histogram).__init__()
		Data = []
		self.__dssBuses = dssBuses
		self.__PlotProperties = PlotProperties
		self.__dssObjectsByClass = dssObjectsbyClass
		self.__index = self.__PlotProperties['index']
		if self.__PlotProperties['ObjectType'] == 'Buses':
			self.Objects = dssBuses
		else:
			self.Objects = self.__dssObjectsByClass[self.__PlotProperties['ObjectType']]
		for ObjName in self.Objects:
			if self.__PlotProperties['ObjectType'] == 'Buses':
				Value = self.Objects[ObjName].GetVariable(self.__PlotProperties['Property'])
			else:
				Value = self.Objects[ObjName].GetValue(self.__PlotProperties['Property'])
			Value = np.multiply(Value, float(self.__PlotProperties['Scaler']))

			if len(Value) == 1:
				Value = float(Value)
			elif self.__index == 'SumEven':
				Value = sum(Value[::2])
			elif self.__index == 'SumOdd':
				Value = sum(Value[1::2])
			elif self.__index == 'MaxEven':
				Value = max(Value[::2])
			elif self.__index == 'MinEven':
				Value = min(Value[::2])
			elif self.__index == 'MaxOdd':
				Value = max(Value[1::2])
			elif self.__index == 'MinOdd':
				Value = min(Value[1::2])
			elif self.__index == 'AvgEven':
				Value = np.mean(Value[1::2])
			elif self.__index == 'AvgOdd':
				Value = np.mean(Value[1::2])
			elif 'Index=' in self.__index:
				c = int(self.__index.replace('Index=', ''))
				Value = Value[c]
			Data.append(Value)
		output_file(PlotProperties['FileName'])
		self.__Figure = figure(plot_width=int(self.__PlotProperties['Width']),
							   plot_height=int(self.__PlotProperties['Height']))  # tools=[hover]

		hhist, hedges = np.histogram(Data, bins=PlotProperties['bins'])

		self.Hist = self.__Figure.quad(top=hhist, bottom=0, left=hedges[:-1], right=hedges[1:],
        fill_color="#036564", line_color="#033649")
		curdoc().add_root(self.__Figure)
		curdoc().title = "PyDSS"

		self.session = push_session(curdoc())
		#self.session.show(self.__Figure)
		return


	def GetSessionID(self):
		return self.session.id

	def GetFigure(self):
		return self.__Figure

	def UpdatePlot(self):
		Data = []
		for ObjName in self.Objects:
			if self.__PlotProperties['ObjectType'] == 'Buses':
				Value = self.Objects[ObjName].GetVariable(self.__PlotProperties['Property'])
			else:
				Value = self.Objects[ObjName].GetValue(self.__PlotProperties['Property'])
			Value = np.multiply(Value, float(self.__PlotProperties['Scaler']))

			if len(Value) == 1:
				Value = float(Value)
			elif self.__index == 'SumEven':
				Value = sum(Value[::2])
			elif self.__index == 'SumOdd':
				Value = sum(Value[1::2])
			elif self.__index == 'MaxEven':
				Value = max(Value[::2])
			elif self.__index == 'MinEven':
				Value = min(Value[::2])
			elif self.__index == 'MaxOdd':
				Value = max(Value[1::2])
			elif self.__index == 'MinOdd':
				Value = min(Value[1::2])
			elif self.__index == 'AvgEven':
				Value = np.mean(Value[1::2])
			elif self.__index == 'AvgOdd':
				Value = np.mean(Value[1::2])
			elif 'Index=' in self.__index:
				c = int(self.__index.replace('Index=', ''))
				Value = Value[c]
			Data.append(Value)
		hhist, hedges = np.histogram(Data, bins=self.__PlotProperties['bins'])
		self.Hist.data_source.data['top']   = hhist
		self.Hist.data_source.data['left']  = hedges[:-1]
		self.Hist.data_source.data['right'] = hedges[1:]

		return 0
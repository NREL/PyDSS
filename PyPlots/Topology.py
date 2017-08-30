
from bokeh.models.widgets import Button, RadioButtonGroup, Select, Slider
from bokeh.plotting import figure, output_file, show
from bokeh.io import output_file, show
from bokeh.layouts import widgetbox, gridplot


class Plot:
	def __init__(self,PlotProperties,dssBuses,dssObjectsByClass):
		self.__dssBuses = dssBuses
		self.__PlotProperties = PlotProperties
		self.__dssObjectsByClass = dssObjectsByClass

		# output to static HTML file
		output_file(PlotProperties['FileName'])
		self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
							 plot_height=self.__PlotProperties['Height'],
							 output_backend="webgl")
		# add a circle renderer with a size, color, and alpha

		self.busX = []
		self.busY = []
		for dssBus in dssBuses.keys():
			XY = dssBuses[dssBus].XY
			if XY[0] > 0 and XY[1] > 0:
				self.busX.append(XY[0])
				self.busY.append(XY[1])
		self.__Figure.circle(self.busX, self.busY, color="navy", alpha=0.5)

		self.LineX = []
		self.LineY = []
		Lines =  dssObjectsByClass['Lines']
		for name, Line in Lines.iteritems():
			Bus1, Bus2 = Line.Bus
			X1, Y1 = dssBuses[Bus1.split('.')[0]].XY
			X2, Y2 = dssBuses[Bus2.split('.')[0]].XY
			if (X1 > 0 and Y1 > 0) and (X2 > 0 and Y2 > 0):
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
						if X > 0 and Y > 0:
							self.ResourceXYbyClass[ObjectClass][0].append(X)
							self.ResourceXYbyClass[ObjectClass][1].append(Y)

		busProperties = dssBuses[dssBuses.keys()[0]].GetVariableNames()
		newbusProperties = []
		for busProperty in busProperties:
			if dssBuses[dssBuses.keys()[0]].DataLength(busProperty)[1] == 'Number' or 'List':
				newbusProperties.append(busProperty)

		LineProperties =

		self.BusPropertySel = Select(title="Bus color property", value='asdsa' , options=newbusProperties)
		self.BusPropertySelVal = RadioButtonGroup(labels=['A', 'B', 'C', 'N','Min','Max','Avg'], active=0)
		self.LinePptySel = Select(title="Line color property", value='asdsa', options=newbusProperties)
		self.LinePptySelVal = RadioButtonGroup(labels=['A', 'B', 'C', 'N', 'Min', 'Max', 'Avg'], active=0)
		self.dssObjectTypeSel = Select(title="Element class:", value="foo", options=dssObjectsByClass.keys())
		self.dssObjValueType = RadioButtonGroup(labels=['Properties', 'Variables'], active=0)
		self.dssObjValue = Select(title="Element class:", value="foo", options=dssObjectsByClass.keys())

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
		print 'YOLO'

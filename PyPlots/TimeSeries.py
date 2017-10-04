from bokeh.models.widgets import Button, RadioButtonGroup, Select, Slider
from bokeh.plotting import figure, output_file, show
from bokeh.io import output_file, show
from bokeh.layouts import widgetbox, gridplot
from bokeh.models import ColumnDataSource, ColorBar, LinearColorMapper , Label

class Plot:
    def __init__(self,PlotProperties, dssBuses, dssObjectsByClass):

        self.__PlotProperties = PlotProperties
        output_file(PlotProperties['FileName'])
        self.__Figure = figure(plot_width=self.__PlotProperties['Width'],
                               plot_height=self.__PlotProperties['Height'])
        self.__Figure.line(PlotProperties['X'],PlotProperties['Y'], line_width=3, line_alpha=0.6)
        show(self.__Figure)
        return


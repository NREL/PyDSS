from bokeh.models.widgets import Button, RadioButtonGroup, Select, Slider
from bokeh.plotting import figure, output_file, show
from bokeh.io import output_file, show
from bokeh.layouts import widgetbox, gridplot






def Plot_Topology(dssBuses,dssObjectsByClass):
    # output to static HTML file
    output_file("line.html")
    p = figure(plot_width=800, plot_height=600, output_backend="webgl")
    # add a circle renderer with a size, color, and alpha

    busX = []
    busY = []
    for dssBus in dssBuses.keys():
        XY = dssBuses[dssBus].XY
        if XY[0] > 0 and XY[1] > 0:
            busX.append(XY[0])
            busY.append(XY[1])

    ResourceXYbyClass = {}
    for ObjectClass in dssObjectsByClass.keys():
        print ObjectClass
        if dssObjectsByClass[ObjectClass]:
            ResourceXYbyClass[ObjectClass] = [[],[]]
            for dssObject in dssObjectsByClass[ObjectClass]:
                Object = dssObjectsByClass[ObjectClass][dssObject]
                if Object.BusCount == 1:
                    BusName = Object.Bus[0].split('.')[0]
                    X,Y = dssBuses[BusName].XY
                    if X > 0 and Y > 0:
                        ResourceXYbyClass[ObjectClass][0].append(X)
                        ResourceXYbyClass[ObjectClass][1].append(Y)

    newXall = []
    newYall = []
    Lines =  dssObjectsByClass['Lines']
    for name, Line in Lines.iteritems():
        Bus1, Bus2 = Line.Bus
        X1, Y1 = dssBuses[Bus1.split('.')[0]].XY
        X2, Y2 = dssBuses[Bus2.split('.')[0]].XY
        if (X1 > 0 and Y1 > 0) and (X2 > 0 and Y2 > 0):
            newXall.append([X1,X2])
            newYall.append([Y1,Y2])

    p.multi_line(newXall, newYall)
    p.circle(busX, busY, color="navy", alpha=0.5)
    value  = ResourceXYbyClass['PVsystems']
    p.square(value[0], value[1], color="red", alpha=0.5)
    busProperties = dssBuses[dssBuses.keys()[0]].GetVariableNames()
    newbusProperties = []
    for busProperty in busProperties:
        if dssBuses[dssBuses.keys()[0]].DataLength(busProperty)[1] == 'Number':
            newbusProperties.append(busProperty)
    print busProperties
    slider = Slider(start=0, end=10, value=1, step=.1, title="Refresh time - [s]")
    selectBus = Select(title="Bus color property", value='asdsa' , options=newbusProperties)
    button_group_busP = RadioButtonGroup(labels=['Phase A', 'Phase B', 'Phase C', 'Phase N','Min','Max'], active=0)
    selectLine = Select(title="Line color property", value='asdsa', options=newbusProperties)
    selectClass = Select(title="Element class:", value="foo", options=dssObjectsByClass.keys())
    button_group = RadioButtonGroup(labels=['Properties', 'Variables'], active=0)
    button_2 = Button(label="Update")
    grid = gridplot([widgetbox(selectBus, button_group_busP, selectLine, selectClass, button_group, button_2, slider, width=300), p], ncols=2)
    # put the results in a row
    show(grid)

    return
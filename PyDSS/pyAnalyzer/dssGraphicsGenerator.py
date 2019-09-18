
import PyDSS.pyAnalyzer.dssPlots.dssFrequencySweep as dssFrequencySweep
import PyDSS.pyAnalyzer.dssPlots.dssGISplot as dssGISplot
import PyDSS.pyAnalyzer.dssPlots.dssPDFplot as dssPDFplot
import PyDSS.pyAnalyzer.dssPlots.dssProfilePlot as dssProfilePlot
import PyDSS.pyAnalyzer.dssPlots.dssXYplot as dssXYplot
import PyDSS.pyAnalyzer.dssPlots.dssVoltageDistance as dssVoltageDistance

class CreatePlots:

    def __init__(self, simulations_args, simulation_results):
        visualization_args = simulations_args['Visualization']
        print(simulation_results)
        if visualization_args['Voltage_sag']:
            dssVoltageDistance.Plot(visualization_args, simulation_results)
        if visualization_args['Voltage_PDF'] or visualization_args['Loading_PDF'] or \
                visualization_args['Voltage_imbalance_PDF']:
            dssPDFplot.Plot(visualization_args, simulation_results)
        if visualization_args['GIS_plot'] or visualization_args['Heat_map']:
            dssGISplot.Plot(visualization_args, simulation_results)
        if visualization_args['Frequency_sweep']:
            dssFrequencySweep.Plot(visualization_args, simulation_results)
        if visualization_args['Voltage_profiles'] or visualization_args['Loading_profiles'] or \
                visualization_args['Load_profiles'] or visualization_args['Generation_profiles'] or \
                visualization_args['Curtailment_profiles'] or visualization_args['Voltage_imbalance_profiles'] or\
                visualization_args['Feederhead_profiles']:
            dssProfilePlot.Plot(visualization_args, simulation_results)
        if visualization_args['Voltage_Loading']:
            dssXYplot.Plot(visualization_args, simulation_results)
        return


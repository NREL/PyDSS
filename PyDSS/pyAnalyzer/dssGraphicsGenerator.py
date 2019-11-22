
import PyDSS.pyAnalyzer.dssPlots.dssFrequencySweep as dssFrequencySweep
import PyDSS.pyAnalyzer.dssPlots.dssGISplot as dssGISplot
import PyDSS.pyAnalyzer.dssPlots.dssPDFplot as dssPDFplot
import PyDSS.pyAnalyzer.dssPlots.dssProfilePlot as dssProfilePlot
import PyDSS.pyAnalyzer.dssPlots.dssXYplot as dssXYplot
import PyDSS.pyAnalyzer.dssPlots.dssVoltageDistance as dssDistance

class CreatePlots:

    required_files = {
        'Voltage_sag': ['Buses-Distance', 'Buses-puVmagAngle'],
        'Voltage': ['Buses-puVmagAngle'],
        'Loading':  {
            'Lines': ['Lines-CurrentsMagAng', 'Lines-normamps'],
            'Transformers': ['Transformers-CurrentsMagAng', 'Transformers-normamps'],
        },
        'Voltage_Loading': {
            'Lines': ['Lines-CurrentsMagAng', 'Lines-normamps', 'Lines-bus1', 'Buses-puVmagAngle'],
            'Transformers': ['Transformers-CurrentsMagAng', 'Transformers-normamps', 'Transformers-bus',
                             'Buses-puVmagAngle'],
        },
        'Load': ['Loads-Powers', 'Loads-VoltagesMagAng'],
        'Generation': {
            'PVSystems': ['PVSystems-Powers', 'PVSystems-VoltagesMagAng'],
            'Generators': ['Generators-Powers', 'Generators-VoltagesMagAng'],
        },
        'Load_Generation': {
            'PVSystems': ['PVSystems-Powers', 'Loads-Powers'],
            'Generators': ['Generators-Powers', 'Loads-Powers'],
        },
        'Curtailment': ['PVSystems-Powers'],
        'XFMR_tap': ['Transformers-taps'],
        'Voltage_imbalance': ['Buses-puVmagAngle'],
        'Frequency_sweep': {
            'Lines': ['Lines-Power', 'Lines-VoltagesMagAng'],
            'Circuits': ['Circuits-TotalPower', 'Circuits-Losses'],
            'Generators': ['Generators-Powers' 'Generators-VoltagesMagAng'],
            'PVSystems': ['PVSystems-Powers', 'PVSystems-VoltagesMagAng'],
            'Loads': ['Loads-Powers', 'Loads-VoltagesMagAng'],
        },
        'Feeder_power': ['Circuits-TotalPower'],
        'Feeder_line_losses': ['Circuits-LineLosses'],
        'Feeder_losses': ['Circuits-Losses'],
        'Feeder_substation_losses': ['Circuits-SubstationLosses'],
    }

    plot_groups = {
        'Even Odd Filter': ['Buses-puVmagAngle', 'Lines-CurrentsMagAng', 'Transformers-CurrentsMagAng',
                            'Loads-Powers', 'Loads-VoltagesMagAng', 'Voltage_imbalance', 'PVSystems-Powers',
                            'PVSystems-VoltagesMagAng', 'Generators-Powers', 'Generators-VoltagesMagAng',
                            'Circuits-TotalPower', 'Circuits-LineLosses', 'Circuits-Losses',
                            'Circuits-SubstationLosses','Transformers-taps']
    }

    plot_Types = {
        'Time series': ['Voltage', 'Loading', 'Load', 'Generation', 'Curtailment','XFMR_tap', 'Voltage_imbalance',
                        'Feeder_power', 'Feeder_line_losses', 'Feeder_substation_losses', 'Feeder_losses'],
        'XY plots': ['Load_Generation', 'Voltage_Loading'],

        'Distance': ['Voltage_sag'],

        'Frequency': ['Frequency_sweep']
    }

    def __init__(self, simulations_args, simulation_results):
        visualization_args = simulations_args['Visualization']
<<<<<<< HEAD
        #print(visualization_args)
=======
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
        plotting_dict = simulations_args['Plots']
        plots = {}
        for plot_type, required_files in self.required_files.items():
            assert (plot_type in plotting_dict),\
                "Define a boolean variable '{}' in the master TOML file".format(plot_type)
            assert (plot_type + '_settings' in visualization_args), \
                "Define settings for the '{}' plot in the master TOML file".format(plot_type)
            if plotting_dict[plot_type] == True:
                plots[plot_type] = {}
                # Validate settings
                for scenario_name, scenario_data in simulation_results.items():
                    scenario_results_formatted = {}
                    plots[plot_type][scenario_name] = {}
                    scenario_settings, scenario_result_obj = scenario_data
                    scenario_results = scenario_result_obj.get_results()
                    scenario_results_formatted = scenario_results.copy()
                    plotsettings = visualization_args[plot_type + '_settings']
                    if isinstance(required_files, dict):
                        assert ('Class' in plotsettings), "Settings for plot type '{}' require ".format(plot_type) +\
<<<<<<< HEAD
                                                          "definition of class variable in the settings dictionary."
=======
                                                          "defination of class variable in the settings dictionary."
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
                        elm_class = plotsettings['Class']
                        required_files = required_files[elm_class]
                    for each_file in required_files:
                        key = self.__check_result_existance(scenario_results, each_file)
                        assert (key != None), "Result for {} do not exist for scenario '{}'.".\
                                                  format(each_file, scenario_name) +\
                                              "Please rerun the ".format(each_file) +\
                                              "simulation and export the required result file to generate a " +\
                                              "'{}' plot".format(plot_type)
                        keysum = [1 for x in self.plot_groups['Even Odd Filter'] if key.startswith(x + '-')]
<<<<<<< HEAD
                        if keysum and plot_type not in self.plot_Types['Frequency']:
=======
                        if keysum:
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
                            scenario_results_formatted[key] = self.__filter_DF_even_odd(scenario_results[key],
                                                                                        plotsettings['Frequency'],
                                                                                        plotsettings['Simulation_mode'])
                        elif plot_type not in self.plot_Types['Frequency']:
                            scenario_results_formatted[key] = self.__filter_DF(scenario_results[key],
                                                                               plotsettings['Frequency'],
                                                                               plotsettings['Simulation_mode'])
<<<<<<< HEAD

                        else:
                            scenario_results_formatted[key] = self.__filter_DF_harmonics(scenario_results[key],
                                                                               plotsettings['Frequency'],
                                                                               plotsettings['Time'],
=======
                        else:
                            scenario_results_formatted[key] = self.__filter_DF_harmonics(scenario_results[key],
                                                                               plotsettings['Timestamp'],
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
                                                                               plotsettings['Simulation_mode'])
                        plots[plot_type][scenario_name]['Data'] = scenario_results_formatted
                        plots[plot_type][scenario_name]['Plot_settings'] = plotsettings
                        plots[plot_type][scenario_name]['Scenario_settings'] = scenario_settings
                        plots[plot_type][scenario_name]['Visualization_settings'] = visualization_args

        self.__create_plots(plots)

<<<<<<< HEAD
    def __filter_DF_harmonics(self, data, baseFreq, time, simulation_mode):
        datax = data.copy()
        datax['Time'] = datax.index
        datax = datax[datax['Time'] == time]
        datax = datax[datax['frequency'] > baseFreq]
        datax = datax[datax['Simulation mode'] == simulation_mode]
        datax.index = datax['frequency']
        datax = datax[datax.columns[2:-1]]
=======
    def __filter_DF_harmonics(self, data, time, simulation_mode):
        datax = data.copy()
        data['Time'] = data.index
        datax = datax[datax['Simulation mode'] == simulation_mode]
        datax = datax[datax.columns[2:]]
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
        return (datax, None)

    def __create_plots(self, plots):
        for plot_type in plots:
            if plot_type in self.plot_Types['Time series']:
                dssProfilePlot.Plot(plot_type, plots[plot_type])
                dssPDFplot.Plot(plot_type, plots[plot_type])
            if plot_type in self.plot_Types['XY plots']:
                dssXYplot.Plot(plot_type, plots[plot_type])
            if plot_type in self.plot_Types['Distance']:
                dssDistance.Plot(plot_type, plots[plot_type])
            if plot_type in self.plot_Types['Frequency']:
                dssFrequencySweep.Plot(plot_type, plots[plot_type])
        return


    def __check_result_existance(self, results, result_key):
        relevant_key = None
        for key in results.keys():
            if key.startswith(result_key):
                relevant_key = key
                break
        return relevant_key

    def __filter_DF_even_odd(self, data, frequecy, simulation_mode):
<<<<<<< HEAD
=======
        # print('###################################################')
        # print(simulation_mode)
        # print(data)
        # print('')
>>>>>>> 98cba91204224c1b5c9e477759bf012e2f70a369
        datax = data[data['frequency'] == frequecy].copy()
        datax = datax[datax['Simulation mode'] == simulation_mode]
        datax = datax[datax.columns[2:]]
        data_even = datax[datax.columns[0::2]]
        data_even = data_even.loc[:, (data_even != 0).any(axis=0)]
        data_odd = datax[datax.columns[1::2]]
        data_odd = data_odd.loc[:, (data_odd != 0).any(axis=0)]
        return data_even, data_odd

    def __filter_DF(self, data, frequecy, simulation_mode):
        datax = data[data['frequency'] == frequecy].copy()
        datax = datax[datax['Simulation mode'] == simulation_mode]
        datax = datax[datax.columns[2:]]
        return (datax, None)

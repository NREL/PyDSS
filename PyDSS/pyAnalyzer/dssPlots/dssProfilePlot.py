import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd
import numpy as np
import warnings
import pathlib
import os

class Plot:

    def __init__(self, plot_type, plot_data):
        scenario_number = 0
        colors = ["#9b59b6", "#3498db", "#95a5a6", "#e74c3c", "#34495e", "#2ecc71"]
        self.legend_lines = []
        self.legend_labels = []
        self.curtailment_data = {}
        visualization_args = None
        two_plots = False
        curtailment_plot = False
        for scenario in plot_data:
            plot_settings = plot_data[scenario]['Plot_settings']
            scenario_settings = plot_data[scenario]['Scenario_settings']
            visualization_args = plot_data[scenario]['Visualization_settings']
            path_seperate, path_single = self.__get_paths(scenario_settings)
            if visualization_args['Plotting_mode'] == "Separate":
                self.legend_lines = []
                self.legend_labels = []
            create_new_plot = visualization_args['Plotting_mode'] == "Separate" or (
                    visualization_args['Plotting_mode'] == "Single" and scenario_number == 0)
            if create_new_plot:
                fig, ax = self.__create_figure(plot_settings['Width'], plot_settings['Height'], plot_settings['DPI'])
                if plot_type in ['Load', 'Generation', 'Feeder_power', 'Feeder_line_losses', 'Feeder_losses',
                                 'Feeder_substation_losses']:
                    fig2, ax2 = self.__create_figure(plot_settings['Width'], plot_settings['Height'], plot_settings['DPI'])
            elm_Class = plot_settings['Class'] if 'Class' in plot_settings else ''
            color = colors[scenario_number % len(colors)]

            if plot_type == 'Voltage':
                two_plots, classes = self.__create_voltage_plot(plot_type, scenario, plot_data, ax, plot_settings,
                                                                color, create_new_plot)
            if plot_type == 'Loading':
                two_plots, classes = self.__create_loading_plot(plot_type, scenario, plot_data, ax, plot_settings,
                                                                color, create_new_plot, elm_Class)
            if plot_type == 'Load':
                two_plots, classes = self.__create_load_plot(plot_type, scenario, plot_data, ax, ax2, plot_settings,
                                                             color, create_new_plot)

            if plot_type == 'Generation':
                two_plots, classes = self.__create_generation_plot(plot_type, scenario, plot_data, ax, ax2,
                                                                   plot_settings, color, create_new_plot, elm_Class)
            if plot_type == 'Curtailment':
                labels_kw = ('Time', 'Active power curtailment [%]')
                key_powers = self.__get_key(plot_data[scenario]['Data'], 'Powers', 'PVSystems')
                data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
                if scenario not in self.curtailment_data:
                    self.curtailment_data[scenario] = {}
                self.curtailment_data[scenario]['labels'] = labels_kw
                self.curtailment_data[scenario]['Data'] = data_kw
                self.curtailment_data[scenario]['Figure'] = fig
                self.curtailment_data[scenario]['Axis'] = ax
                self.curtailment_data[scenario]['Settings'] = plot_settings
                self.curtailment_data[scenario]['Color'] = colors[scenario_number % len(colors)]
                self.curtailment_data[scenario]['Path_seperate'] = path_seperate
                self.curtailment_data[scenario]['Path_single'] = path_single
                classes = None
                curtailment_plot = True

            if plot_type == 'Voltage_imbalance':
                two_plots, classes = self.__create_voltage_imbalance_plot(plot_type, scenario, plot_data, ax,
                                                                          plot_settings, color, create_new_plot)

            if plot_type == 'Feeder_power':
                two_plots, classes = self.__create_feeder_power_plot(plot_type, scenario, plot_data, ax, ax2,
                                                                   plot_settings, color, create_new_plot)
            if plot_type == 'Feeder_line_losses':
                two_plots, classes = self.__create_feeder_llosses_plot(plot_type, scenario, plot_data, ax, ax2,
                                                                   plot_settings, color, create_new_plot)
            if plot_type == 'Feeder_substation_losses':
                two_plots, classes = self.__create_feeder_slosses_plot(plot_type, scenario, plot_data, ax, ax2,
                                                                   plot_settings, color, create_new_plot)
            if plot_type == 'Feeder_losses':
                two_plots, classes = self.__create_feeder_losses_plot(plot_type, scenario, plot_data, ax, ax2,
                                                                   plot_settings, color, create_new_plot)
            if plot_type == 'XFMR_tap':
                two_plots, classes = self.__create_xfmr_tap_plot(plot_type, scenario, plot_data, ax, plot_settings,
                                                                 color, create_new_plot)
            if classes:
                elm_Class, elm_Class2 = classes

            if visualization_args['Plotting_mode'] == "Separate" and plot_type != 'Curtailment':
                self.save_file(fig, path_seperate, scenario, '{}-{}'.format(elm_Class, plot_type),
                               visualization_args['FileType'])
                if two_plots:
                    self.save_file(fig2, path_seperate, scenario, '{}-{}'.format(elm_Class2, plot_type),
                                   visualization_args['FileType'])

            scenario_number += 1
        if visualization_args and visualization_args['Plotting_mode'] == "Single" and plot_type != 'Voltage_imbalance':
            self.save_file(fig, path_single, scenario, '{}-{}'.format(elm_Class, plot_type),
                           visualization_args['FileType'])
            if two_plots:
                self.save_file(fig2, path_single, scenario, '{}-{}'.format(elm_Class2, plot_type),
                               visualization_args['FileType'])

        if curtailment_plot:
            scenarios = list(self.curtailment_data.keys())
            base_scenario = scenarios[0]
            builtup_scenario = scenarios[1:]
            for sen in builtup_scenario:
                data = (self.curtailment_data[base_scenario]['Data'] - self.curtailment_data[sen]['Data']) / \
                       self.curtailment_data[base_scenario]['Data'] * 100
                data = data.fillna(0)
                if visualization_args['Plotting_mode'] == "Separate":
                    self.__generate_plot(ax=self.curtailment_data[sen]['Axis'],
                                         labels=self.curtailment_data[sen]['labels'],
                                         data=data, plot_settings=self.curtailment_data[sen]['Settings'],
                                         scenario=sen, color=self.curtailment_data[sen]['Color'],
                                         newplot=False)
                    self.save_file(self.curtailment_data[sen]['Figure'],
                                   self.curtailment_data[sen]['Path_seperate'], scenario,
                                   '{}-{}'.format('', plot_type), visualization_args['FileType'])
                if visualization_args and visualization_args['Plotting_mode'] == "Single":
                    self.__generate_plot(ax=self.curtailment_data[builtup_scenario[-1]]['Axis'],
                                         labels=self.curtailment_data[builtup_scenario[-1]]['labels'],
                                         data=data, plot_settings=self.curtailment_data[builtup_scenario[-1]]['Settings'],
                                         scenario=sen, color=self.curtailment_data[builtup_scenario[-1]]['Color'],
                                         newplot=False)
                    self.save_file(self.curtailment_data[sen]['Figure'],
                                   self.curtailment_data[builtup_scenario[-1]]['Path_single'],
                                   builtup_scenario[-1], '{}-{}'.format('', plot_type),
                                   visualization_args['FileType'])
        return

    def __create_xfmr_tap_plot(self, plot_type, scenario, plot_data, ax, plot_settings, color, create_new_plot):
        labels = ('Time', plot_type + ' [p.u.]')
        key = self.__get_key(plot_data[scenario]['Data'], 'Transformers-taps', None)
        data = self.__get_data(plot_data[scenario]['Data'][key])
        self.__generate_plot(ax=ax, labels=labels, data=data, plot_settings=plot_settings, scenario=scenario,
                             color=color, newplot=create_new_plot)
        return False, None

    def __create_feeder_losses_plot(self, plot_type, scenario, plot_data, ax, ax2,  plot_settings, color,
                                   create_new_plot):
        labels_kw = ('Time', 'Total losses (active power) [kW]')
        labels_kvar = ('Time', 'Total  losses (reactive power)[kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Circuits-Losses', None)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False)
        self.__generate_plot(ax=ax, labels=labels_kw, data=data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        elm_Class2 = 'losses-[kVAr]'
        elm_Class = 'losses-[kW]'
        return True, (elm_Class, elm_Class2)

    def __create_feeder_slosses_plot(self, plot_type, scenario, plot_data, ax, ax2,  plot_settings, color,
                                   create_new_plot):
        labels_kw = ('Time', 'Substation losses (active power) [kW]')
        labels_kvar = ('Time', 'Substation  losses (reactive power)[kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Circuits-SubstationLosses', None)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers]).abs()
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False).abs()
        self.__generate_plot(ax=ax, labels=labels_kw, data=data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        elm_Class2 = 'sublosses-[kVAr]'
        elm_Class = 'sublosses-[kW]'
        return True, (elm_Class, elm_Class2)

    def __create_feeder_llosses_plot(self, plot_type, scenario, plot_data, ax, ax2,  plot_settings, color,
                                   create_new_plot):
        labels_kw = ('Time', 'Line losses (active power)[kW]')
        labels_kvar = ('Time', 'Line losses (reactive power)[kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Circuits-LineLosses', None)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers]).abs()
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False).abs()
        self.__generate_plot(ax=ax, labels=labels_kw, data=data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        elm_Class2 = 'linelosses-[kVAr]'
        elm_Class = 'linelosses-[kW]'
        return True, (elm_Class, elm_Class2)

    def __create_feeder_power_plot(self, plot_type, scenario, plot_data, ax, ax2,  plot_settings, color,
                                   create_new_plot):
        labels_kw = ('Time', 'Feeder active power demand [kW]')
        labels_kvar = ('Time', 'Feeder reactive power demand [kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Circuits-TotalPower', None)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False)
        self.__generate_plot(ax=ax, labels=labels_kw, data=-data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=-data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        elm_Class2 = 'Circuit-[kVAr]'
        elm_Class = 'Circuit-[kW]'
        return True, (elm_Class, elm_Class2)

    def __create_voltage_imbalance_plot(self, plot_type, scenario, plot_data, ax, plot_settings, color, create_new_plot):
        labels = ('Time', plot_type + ' [%]')
        key = self.__get_key(plot_data[scenario]['Data'], 'Buses-puVmagAngle', None)
        data = self.__get_data(plot_data[scenario]['Data'][key])
        buses = [set(['{} ph:{} [V:pu]'.format(x.split(' ')[0], i) for i in range(1, 4)]) for x in data.columns]
        completed_sets = []
        imbalance = pd.DataFrame()
        for bus in buses:
            if bus not in completed_sets:
                completed_sets.append(bus)
                bus_intersection = bus.intersection(set(data.columns))
                if len(bus_intersection) > 1:
                    for i in range(len(bus_intersection)):
                        for j in range(len(bus_intersection)):
                            if j > i:
                                bus_name = list(bus_intersection)[0].split(' ')[0]
                                label = '{} Ph {} - Ph {}'.format(bus_name, i + 1, j + 1)
                                imbalance[label] = np.abs((data['{} ph:{} [V:pu]'.format(bus_name, i + 1)] -
                                                           data['{} ph:{} [V:pu]'.format(bus_name, j + 1)]) * 100)
        self.__generate_plot(ax=ax, labels=labels, data=imbalance, plot_settings=plot_settings, scenario=scenario,
                             color=color, newplot=create_new_plot)
        return False, None

    def __create_generation_plot(self, plot_type, scenario, plot_data, ax, ax2, plot_settings, color, create_new_plot,
                           elm_Class):
        labels_kw = ('Time', 'Active power generation [kW]')
        labels_kvar = ('Time', 'Reactive power generation [kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Powers', elm_Class)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False)
        self.__generate_plot(ax=ax, labels=labels_kw, data=-data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color,  newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=-data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color,  newplot=create_new_plot)

        elm_Class2 = '{}[kVAr]'.format(elm_Class)
        elm_Class = '{}[kW]'.format(elm_Class)
        return True, (elm_Class, elm_Class2)

    def __create_load_plot(self, plot_type, scenario, plot_data, ax, ax2, plot_settings, color, create_new_plot):
        labels_kw = ('Time', 'Active power demand [kW]')
        labels_kvar = ('Time', 'Reactive power demand [kVAr]')
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Loads-Powers', None)
        data_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        data_kvar = self.__get_data(plot_data[scenario]['Data'][key_powers], False)
        self.__generate_plot(ax=ax, labels=labels_kw, data=data_kw, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        self.__generate_plot(ax=ax2, labels=labels_kvar, data=data_kvar, plot_settings=plot_settings,
                             scenario=scenario, color=color, newplot=create_new_plot)
        elm_Class = 'load[kW]'
        elm_Class2 = 'load[kVAr]'
        return True, (elm_Class, elm_Class2)

    def __create_voltage_plot(self, plot_type, scenario, plot_data, ax, plot_settings, color, create_new_plot):
        labels = ('Time', plot_type + ' [p.u.]')
        key = self.__get_key(plot_data[scenario]['Data'], 'Buses-puVmagAngle', None)
        data = self.__get_data(plot_data[scenario]['Data'][key])
        self.__generate_plot(ax=ax, labels=labels, data=data, plot_settings=plot_settings, scenario=scenario,
                             color=color, newplot=create_new_plot)
        return False, None

    def __create_loading_plot(self, plot_type, scenario, plot_data, ax, plot_settings, color, create_new_plot,
                              elm_Class):
        labels = ('Time', elm_Class[:-1] + ' ' + plot_type.lower() + ' [%]')
        key = self.__get_key(plot_data[scenario]['Data'], 'CurrentsMagAng', plot_settings['Class'])
        data_current_magnitude = self.__get_data(plot_data[scenario]['Data'][key])
        key_normamps = self.__get_key(plot_data[scenario]['Data'], 'normamps', plot_settings['Class'])
        data_normamps = self.__get_data(plot_data[scenario]['Data'][key_normamps])
        current_cols = [x.split(' ')[0] for i, x in enumerate(data_current_magnitude.columns)]
        loading = pd.DataFrame()
        for c1, c2 in zip(data_current_magnitude.columns, current_cols):
            loading[c1] = data_current_magnitude[c1] / data_normamps[c2 + ' [Amp]'] * 100
        self.__generate_plot(ax=ax, labels=labels, data=loading, plot_settings=plot_settings, scenario=scenario,
                             color=color, newplot=create_new_plot)
        return False, None

    def __get_key(self, data_dict, filetag, elm_class):
        if elm_class == None:
            key = [x for x in data_dict if x.startswith('{}-'.format(filetag))][0]
        else:
            key = [x for x in data_dict if x.startswith('{}-{}-'.format(elm_class, filetag))][0]
        return key

    def __get_data(self, data, even=True):
        if isinstance(data, tuple):
            data_even, data_odd = data
            if not even:
                data_even = data_odd
        else:
            data_even = data
        return data_even

    def __generate_plot(self,  ax, labels, data, plot_settings, color, scenario, newplot):
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.dropna()
        data.index = pd.to_datetime(data.index)
        try:
            range = np.max(data.values) - np.min(data.values)
            ax.set_ylim(np.min(data.values) - 0.05 * range,  np.max(data.values) + 0.05 * range)
            ax = data.plot(ax=ax, color=color, alpha=plot_settings['Line_alpha'],
                                 linewidth=plot_settings['Line_width'])

            ax.set_xlabel(list(labels)[0])
            ax.set_ylabel(list(labels)[1])
            if plot_settings['Grid']:
                ax.grid(color='lightgrey', linestyle='-', linewidth=0.3)
            if 'Show_operation_regions' in plot_settings and plot_settings['Show_operation_regions'] and newplot:
                for i, label in enumerate(plot_settings['Y_range_labels']):
                    b1 = ax.axhspan(plot_settings['Y_ranges'][i], plot_settings['Y_ranges'][i + 1], alpha=0.03,
                                    color=plot_settings['Y_range_colors'][i], label='normal loading region')
                    self.legend_lines.append(b1)
                    self.legend_labels.append(label)
            self.legend_lines.append(ax.lines[-1])
            self.legend_labels.append(scenario)
            legend = ax.legend(self.legend_lines, self.legend_labels, frameon=False,
                               prop={'size': plot_settings['Legend_font_size']})
            plt.tight_layout()
        except:
            warnings.warn("Data error: No plot created")
        return

    def __get_paths(self, simulation_settings):
        path_seperate = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                                    "Exports", simulation_settings["Active Scenario"], "Plots")
        path_single = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                                     "Exports", simulation_settings["Active Scenario"], "Scenario Comparison Plots")
        return path_seperate, path_single

    def __create_figure(self, width, height, dpi):
        fig = plt.figure(figsize=(width, height), dpi=dpi)
        ax = fig.add_subplot(111)
        return fig, ax

    def save_file(self, figure, path, scenario,plot_type, extension):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        figpath = '{}\{}-{}-TS.{}'.format(path, scenario, plot_type, extension)
        figure.savefig(figpath)
        plt.close(figure)
        print("File saved: {}".format(figpath))
        return
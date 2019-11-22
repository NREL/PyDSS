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
            elm_Class = plot_settings['Class'] if 'Class' in plot_settings else ''
            color = colors[scenario_number % len(colors)]
            two_plots, classes = self.__create_frequency_plot(plot_type, scenario, plot_data, ax, plot_settings,
                                                                color, create_new_plot)

            scenario_number += 1

            if visualization_args['Plotting_mode'] == "Separate" and plot_type != 'Curtailment':
                self.save_file(fig, path_seperate, scenario, '{}-{}'.format(elm_Class, plot_type),
                               visualization_args['FileType'])
            scenario_number += 1
        if visualization_args and visualization_args['Plotting_mode'] == "Single" and plot_type != 'Voltage_imbalance':
            self.save_file(fig, path_single, scenario, '{}-{}'.format(elm_Class, plot_type),
                           visualization_args['FileType'])
        return

    def __create_frequency_plot(self, plot_type, scenario, plot_data, ax, plot_settings, color, create_new_plot):
        labels = ('Frequency [Hz]', 'Value')
        key = self.__get_key(plot_data[scenario]['Data'], None, plot_settings['Class'])
        data = self.__get_data(plot_data[scenario]['Data'][key])
        self.__generate_plot(ax=ax, labels=labels, data=data, plot_settings=plot_settings, scenario=scenario,
                             color=color, newplot=create_new_plot)
        return False, None


    def __get_key(self, data_dict, filetag=None, elm_class=None):
        if elm_class == None:
            key = [x for x in data_dict if x.startswith('{}-'.format(filetag))][0]
        elif filetag == None:
            key = [x for x in data_dict if x.startswith('{}-'.format(elm_class))][0]
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

        ax = data.plot(ax=ax, color=color, alpha=plot_settings['Line_alpha'], linewidth=plot_settings['Line_width'])
        markers = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', 'P', 'X']
        for i, line in enumerate(ax.get_lines()):
            line.set_marker(markers[i])

        ax.set_xlabel(list(labels)[0])
        ax.set_ylabel(list(labels)[1])
        if plot_settings['Grid']:
            ax.grid(color='lightgrey', linestyle='-', linewidth=0.3)

        legend = ax.legend(ax.get_lines(), data.columns, frameon=False,
                           prop={'size': plot_settings['Legend_font_size']})
        plt.tight_layout()
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
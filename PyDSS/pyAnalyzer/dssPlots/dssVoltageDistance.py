import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd
import pathlib
import os

class Plot:

    def __init__(self, visualization_args, simulation_results):
        self.simulation_results = simulation_results
        self.visualization_args = visualization_args

        if visualization_args['Voltage_sag']:
            self.__create_voltage_sag_plot(visualization_args, simulation_results)

        return

    def __create_voltage_sag_plot(self, visualization_args, simulation_results):
        plot_settings = visualization_args['Voltage_sag_settings']
        width = visualization_args['Global_width'] if visualization_args['Global_override'] else  plot_settings['Width']
        height = visualization_args['Global_height'] if visualization_args['Global_override'] else  plot_settings['Height']
        dpi = visualization_args['Global_DPI'] if visualization_args['Global_override'] else  plot_settings['DPI']
        first_scenario = True
        simulation_key = None
        fig = None
        ax = None
        colors = ["#9b59b6", "#3498db", "#95a5a6", "#e74c3c", "#34495e", "#2ecc71"]
        c = 0
        lines = []
        labels = []

        for simulation_key, value in simulation_results.items():
            if visualization_args['Plotting_mode'] == "Separate" or (
                    visualization_args['Plotting_mode'] == "Single" and first_scenario):
                fig, ax = self.__create_figure(width, height, dpi, 'Distance [Mi]', 'Voltage magnitude [p.u.]')
            simulation_settings, result_obj = value
            ExportFolder = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                "Exports", simulation_settings["Active Scenario"], "Plots")
            ExportFolder2 = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                                        "Exports", simulation_settings["Active Scenario"], "Scenario Comparison Plots")
            results = result_obj.get_results()
            relevant_key = self.__check_result_existance(results, 'Buses-puVmagAngle')
            relevant_dist_key = self.__check_result_existance(results, 'Buses-Distance')
            if relevant_key != None and relevant_dist_key != None:
                plotdata = self.__filter_DF_magntitudes(results[relevant_key], plot_settings['Frequency'],
                                                        plot_settings['Simulation_mode'])
                plotdata = plotdata.loc[plot_settings['Time']]
                distdata = results[relevant_dist_key].loc[plot_settings['Time']]
                distances = []
                for c1 in [x.split(" ")[0] for x in plotdata.index]:
                    distances.append(distdata.loc[c1 + ' [Mi]'])
                voltages = plotdata.values

                if visualization_args['Plotting_mode'] == "Separate" or (
                        visualization_args['Plotting_mode'] == "Single" and first_scenario):
                    if plot_settings['display_limits']:
                        b1 = ax.axhspan(plot_settings['UV'][0], plot_settings['OV'][0], alpha=0.05,
                                        color='darkolivegreen', label='normal region')
                        b2 = ax.axhspan(plot_settings['UV'][0], plot_settings['UV'][1], alpha=0.05,
                                        color='darkgoldenrod', label='control region')
                        b3 = ax.axhspan(plot_settings['UV'][1], plot_settings['UV'][2], alpha=0.05, color='darkorange',
                                        label='curtailment region')
                        b4 = ax.axhspan(plot_settings['UV'][2], 0.0, alpha=0.1, color='darkred', label='trip region')
                        b5 = ax.axhspan(plot_settings['OV'][0], plot_settings['OV'][1], alpha=0.05,
                                        color='darkgoldenrod')
                        b6 = ax.axhspan(plot_settings['OV'][1], plot_settings['OV'][2], alpha=0.05, color='darkorange')
                        b7 = ax.axhspan(plot_settings['OV'][2], 1.2, alpha=0.1, color='darkred')

                        lines.extend([b1, b2, b3, b4])
                        labels.extend(['normal region', 'control region', 'curtailment region', 'trip region'])
                        for b, h in zip([b1, b2, b3, b4, b5, b6, b7], ['\\\\', 'x', '//', '+', 'x', '//', '+']):
                            b.set_hatch(h)
                yrange = (max(voltages) - min(voltages)) * 0.05

                ax.set_ylim(min(voltages) - yrange, max(voltages) + yrange)
                line = ax.scatter(distances, voltages)
                lines.append(line)
                labels.append(simulation_key)
                leg = ax.legend(lines, labels, frameon=False, prop={'size': plot_settings['Legend_font_size']})
                for lh in leg.legendHandles:
                    lh.set_alpha(0.6)
                if plot_settings['Grid']:
                    ax.grid(color='lightgrey', linestyle='-')
                fig.tight_layout()
                if visualization_args['Plotting_mode'] == "Separate":
                    self.save_file(fig, ExportFolder, simulation_key, 'voltage_sag', visualization_args['FileType'])

            first_scenario = False
            c+=1
        if visualization_args['Plotting_mode'] == "Single":
            self.save_file(fig, ExportFolder2, simulation_key, 'voltage_sag', visualization_args['FileType'])
        return

    def __check_result_existance(self, results, result_key):
        relevant_key = None
        for key in results.keys():
            if key.startswith(result_key):
                relevant_key = key
                break
        return relevant_key

    def __filter_DF_magntitudes(self, data, frequecy, simulation_mode):
        data = data[data['frequency'] == frequecy]
        data = data[data['Simulation mode'] == simulation_mode]
        data = data[data.columns[2:]]
        data = data[data.columns[::2]]
        data = data.loc[:, (data != 0).any(axis=0)]
        return data

    def __create_figure(self, width, height, dpi, xlabel, ylabel):
        fig = plt.figure(figsize=(width, height), dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        return fig, ax

    def save_file(self, figure, path, scenario,plot_type, extension):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        figpath = '{}\{}-{}.{}'.format(path, scenario, plot_type, extension)
        figure.savefig(figpath)
        print("File saved: {}".format(figpath))
        return
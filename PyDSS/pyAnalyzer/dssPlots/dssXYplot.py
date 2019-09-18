import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd
import pathlib
import os

class Plot:

    def __init__(self, visualization_args, simulation_results):
        self.simulation_results = simulation_results
        self.visualization_args = visualization_args

        if visualization_args['Voltage_Loading']:
            self.__create_voltage_loading_plot(visualization_args, simulation_results)
        return

    def __create_voltage_loading_plot(self, visualization_args, simulation_results):
        plot_settings = visualization_args['Loading_PDF_settings']
        width = visualization_args['Global_width'] if visualization_args['Global_override'] else plot_settings['Width']
        height = visualization_args['Global_height'] if visualization_args['Global_override'] else plot_settings[
            'Height']
        dpi = visualization_args['Global_DPI'] if visualization_args['Global_override'] else plot_settings['DPI']
        first_scenario = True
        simulation_key = None
        simulation_settings = None
        for simulation_key, value in simulation_results.items():
            if visualization_args['Plotting_mode'] == "Separate" or (
                    visualization_args['Plotting_mode'] == "Single" and first_scenario):
                fig = plt.figure(figsize=(width, height), dpi=dpi)
                ax = fig.add_subplot(111)
                ax.set_xlabel('Line loading [%]')
                ax.set_ylabel('Voltage magnitude [p.u.]')

            simulation_settings, result_obj = value
            results = result_obj.get_results()
            current_file_exist = False
            normamp_file_exist = False
            voltage_file_exist = False
            relevant_key_voltage = None
            relevant_key_normamps = None
            relevant_key_current = None
            for key in results.keys():
                if key.startswith('Lines-normamps'):
                    normamp_file_exist = True
                    relevant_key_normamps = key
                    break

            for key in results.keys():
                if key.startswith('Lines-CurrentsMagAng'):
                    current_file_exist = True
                    relevant_key_current = key
                    break

            for key in results.keys():
                if key.startswith('Buses-puVmagAngle'):
                    voltage_file_exist = True
                    relevant_key_voltage = key
                    break

            if current_file_exist and normamp_file_exist and voltage_file_exist:
                norm_amps = results[relevant_key_normamps]
                currents = results[relevant_key_current]
                currents = currents[currents.columns[2:]]
                currents = currents[currents.columns[::2]]
                currents = currents.loc[:, (currents != 0).any(axis=0)]
                current_cols = [x.split(' ')[0] for i, x in enumerate(currents.columns)]
                loading = pd.DataFrame()
                for c1, c2 in zip(currents.columns, current_cols):
                    loading[c1] = currents[c1] / norm_amps[c2 + ' [Amp]'] * 100

                voltages = results[relevant_key_voltage]
                voltages = voltages[voltages['frequency'] == plot_settings['Frequency']]
                voltages = voltages[voltages['Simulation mode'] == plot_settings['Simulation_mode']]
                voltages = voltages[voltages.columns[2:]]
                voltages = voltages[voltages.columns[::2]]
                voltages = voltages.loc[:, (voltages != 0).any(axis=0)]
                voltage_cols = [x.replace(' [V:pu]', '') for x in voltages.columns]
                print(loading)
                print(voltages)
                break

                plotdata = loading.values.flatten()

                sbn.distplot(
                    plotdata,
                    ax=ax,
                    label=simulation_key,
                    hist_kws=dict(alpha=plot_settings['Alpha']),
                    norm_hist=False,
                    kde=True,
                )

                ax.legend(prop={'size': plot_settings['Legend_font_size']})
                if plot_settings['Grid']:
                    ax.grid(color='lightgrey', linestyle='-')
                fig.tight_layout()
                if visualization_args['Plotting_mode'] == "Separate":
                    ExportFolder = os.path.join(
                        simulation_settings["Project Path"],
                        simulation_settings["Active Project"],
                        "Exports",
                        simulation_settings["Active Scenario"],
                        "Plots"
                    )
                    self.save_file(fig, ExportFolder, simulation_key, 'loadingPDF', visualization_args['FileType'])

            if visualization_args['Plotting_mode'] == "Single":
                ExportFolder = os.path.join(
                    simulation_settings["Project Path"],
                    simulation_settings["Active Project"],
                    "Exports",
                    simulation_settings["Active Scenario"],
                    "Scenario Comparison Plots"
                )
                self.save_file(fig, ExportFolder, simulation_key, 'loadingPDF', visualization_args['FileType'])
            first_scenario = False
        return
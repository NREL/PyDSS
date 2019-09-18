import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd
import pathlib
import os

class Plot:

    def __init__(self, visualization_args, simulation_results):
        self.simulation_results = simulation_results
        self.visualization_args = visualization_args

        if visualization_args['Voltage_PDF']:
            self.__create_voltage_pdf_plot(visualization_args, simulation_results)
        if visualization_args['Loading_PDF']:
            self.__create_loading_pdf_plot(visualization_args, simulation_results)
        return

    def __create_loading_pdf_plot(self, visualization_args, simulation_results):
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
                fig = plt.figure(figsize=(width,height), dpi=dpi)
                ax = fig.add_subplot(111)
                ax.set_xlabel('Line loading [%]')
                ax.set_ylabel('Frequency')

            simulation_settings, result_obj = value
            results = result_obj.get_results()
            current_file_exist = False
            normamp_file_exist = False
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

            if current_file_exist and normamp_file_exist:
                norm_amps = results[relevant_key_normamps]
                currents = results[relevant_key_current]
                currents = currents[currents['frequency'] == plot_settings['Frequency']]
                currents = currents[currents['Simulation mode'] == plot_settings['Simulation_mode']]
                currents = currents[currents.columns[2:]]
                currents = currents[currents.columns[::2]]
                currents = currents.loc[:, (currents != 0).any(axis=0)]
                current_cols = [x.split(' ')[0] for i, x in enumerate(currents.columns)]
                loading = pd.DataFrame()
                for c1, c2 in zip(currents.columns, current_cols):
                    loading[c1] = currents[c1] / norm_amps[c2 + ' [Amp]'] * 100
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

    def __create_voltage_pdf_plot(self, visualization_args, simulation_results):
        plot_settings = visualization_args['Voltage_PDF_settings']
        width = visualization_args['Global_width'] if visualization_args['Global_override'] else  plot_settings['Width']
        height = visualization_args['Global_height'] if visualization_args['Global_override'] else  plot_settings['Height']
        dpi = visualization_args['Global_DPI'] if visualization_args['Global_override'] else  plot_settings['DPI']
        first_scenario = True
        simulation_key = None
        simulation_settings = None
        for simulation_key, value in simulation_results.items():
            if visualization_args['Plotting_mode'] == "Separate" or (
                    visualization_args['Plotting_mode'] == "Single" and first_scenario):
                fig = plt.figure(figsize=(width,height), dpi=dpi)
                ax = fig.add_subplot(111)
                ax.set_xlabel('Voltage magnitude [p.u.]')
                ax.set_ylabel('Frequency')

            simulation_settings, result_obj = value
            results = result_obj.get_results()
            results_exist = False
            relevant_key = None
            for key in results.keys():
                if key.startswith('Buses-puVmagAngle'):
                    results_exist = True
                    relevant_key = key
                    break

            if results_exist:
                plotdata = results[relevant_key]
                plotdata = plotdata[plotdata['frequency'] == plot_settings['Frequency']]
                plotdata = plotdata[plotdata['Simulation mode'] == plot_settings['Simulation_mode']]
                plotdata = plotdata[plotdata.columns[2:]]
                plotdata = plotdata[plotdata.columns[::2]]
                plotdata = plotdata.loc[:, (plotdata != 0).any(axis=0)]
                plotdata = plotdata.values.flatten()


                #plotdata.plot.hist()
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
                    self.save_file(fig, ExportFolder, simulation_key, 'VpuPDF', visualization_args['FileType'])
                    #ax.tight_layout()
            first_scenario = False

        if visualization_args['Plotting_mode'] == "Single":
            ExportFolder = os.path.join(
                simulation_settings["Project Path"],
                simulation_settings["Active Project"],
                "Exports",
                simulation_settings["Active Scenario"],
                "Scenario Comparison Plots"
            )
            self.save_file(fig, ExportFolder, simulation_key, 'VpuPDF', visualization_args['FileType'])
        return


    def save_file(self, figure, path, scenario,plot_type, extension):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        figure.savefig('{}\{}-{}.{}'.format(
            path,
            scenario,
            plot_type,
            extension,
        ))
        return
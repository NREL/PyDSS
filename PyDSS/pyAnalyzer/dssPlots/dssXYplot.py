import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd
import numpy as np
import pathlib
import os


class Plot:
    def __init__(self, plot_type, plot_data):
        colormaps = [
            'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn'
        ]
        X_Y_dataframes = []
        scenario_number = 0
        plot_settings = None
        visualization_args = None
        for scenario in plot_data:
            plot_settings = plot_data[scenario]['Plot_settings']
            scenario_settings = plot_data[scenario]['Scenario_settings']
            visualization_args = plot_data[scenario]['Visualization_settings']
            height = plot_settings['Height']
            path_seperate, path_single = self.__get_paths(scenario_settings)
            if visualization_args['Plotting_mode'] == "Separate":
                self.legend_lines = []
                self.legend_labels = []
            create_new_plot = visualization_args['Plotting_mode'] == "Separate" or (
                    visualization_args['Plotting_mode'] == "Single" and scenario_number == 0)
            elm_Class = plot_settings['Class'] if 'Class' in plot_settings else ''
            color = colormaps[scenario_number % len(colormaps)]
            if plot_type == 'Voltage_Loading':
                X_Y_dataframes.append(self.__get_voltage_loading_data(
                        plot_data=plot_data, scenario=scenario, plot_settings=plot_settings, elm_Class=elm_Class
                ))
            if plot_type == 'Load_Generation':
                X_Y_dataframes.append(self.__get_load_generation_data(
                    plot_data=plot_data, scenario=scenario, plot_settings=plot_settings, elm_Class=elm_Class
                ))
            if visualization_args['Plotting_mode'] == "Separate":
                columns = X_Y_dataframes[-1].columns
                X = X_Y_dataframes[-1][columns[0]].values
                Y = X_Y_dataframes[-1][columns[1]].values
                sbn.set(style="white")
                joint_plot = sbn.jointplot(X, Y, kind=plot_settings["Kind"], height=height, space=0, cmap=color)
                joint_plot.fig.axes[0].set_ylabel('Line loading [%]')
                joint_plot.fig.axes[0].set_xlabel('Voltage magnitude [p.u.]')
                joint_plot.fig.tight_layout()
                self.save_file(joint_plot.fig, path_seperate, scenario, '{}-VLplot'.format(plot_settings['Class']),
                               visualization_args['FileType'])
            scenario_number += 1
        if visualization_args['Plotting_mode'] == "Single":
            df = pd.concat(X_Y_dataframes)
            columns =df.columns
            self.multivariateGrid(columns[0], columns[1], columns[2], df=df, kind=plot_settings["Kind"])
            self.save_file(plt.gcf(), path_single, scenario, '{}-VLplot'.format(plot_settings['Class']),
                                   visualization_args['FileType'])

        return

    def __get_load_generation_data(self, plot_data, scenario, plot_settings, elm_Class):
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Powers', elm_Class)
        generation_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        key_powers = self.__get_key(plot_data[scenario]['Data'], 'Loads-Powers', None)
        load_kw = self.__get_data(plot_data[scenario]['Data'][key_powers])
        load = load_kw.sum(axis=1).values
        generation = (-generation_kw.sum(axis=1)).values
        parsed_data = pd.DataFrame(np.matrix([load, generation]).T, columns=[
            'Total active power demand [kW]',
            'Total generation from "{}" [kW]'.format(plot_settings['Class'])])
        parsed_data['kind'] = scenario
        return parsed_data


    def __get_voltage_loading_data(self, plot_data, scenario, plot_settings, elm_Class):
        key = self.__get_key(plot_data[scenario]['Data'], 'CurrentsMagAng', plot_settings['Class'])
        currents = self.__get_data(plot_data[scenario]['Data'][key])

        key_normamps = self.__get_key(plot_data[scenario]['Data'], 'normamps', plot_settings['Class'])
        norm_amps = self.__get_data(plot_data[scenario]['Data'][key_normamps])

        key = self.__get_key(plot_data[scenario]['Data'], 'Buses-puVmagAngle', None)
        voltages = self.__get_data(plot_data[scenario]['Data'][key])

        if elm_Class == 'Transformers':
            key = self.__get_key(plot_data[scenario]['Data'], 'bus', plot_settings['Class'])
            line_bus = self.__get_data(plot_data[scenario]['Data'][key])
        else:
            key = self.__get_key(plot_data[scenario]['Data'], 'bus1', plot_settings['Class'])
            line_bus = self.__get_data(plot_data[scenario]['Data'][key])

        current_cols = [x.split(' ')[0] for i, x in enumerate(currents.columns)]
        loading = pd.DataFrame()
        line_voltages = pd.DataFrame()
        for c1, c2 in zip(currents.columns, current_cols):
            loading[c1] = currents[c1] / norm_amps[c2 + ' [Amp]'] * 100
            busInfo = str(line_bus[c2].tolist()[0])
            busInfo = busInfo.split('.')
            bus = busInfo[0]
            phases = busInfo[1:]
            for p in phases:
                col_name = '{} ph:{} [V:pu]'.format(bus, p)
                if col_name in voltages:
                    line_voltages[c1] = voltages[col_name]

        common_cols = list(set(loading.columns).intersection(set(line_voltages.columns)))
        loading = loading[common_cols].values.flatten()
        line_voltages = line_voltages[common_cols].values.flatten()

        parsed_data = pd.DataFrame(np.matrix([line_voltages, loading]).T, columns=[
            'Voltage magnitude [p.u.]',
            '{} loading [%]'.format(plot_settings['Class'][:-1])])
        parsed_data['kind'] = scenario
        return parsed_data

    def __get_data(self, data, even=True):
        if isinstance(data, tuple):
            data_even, data_odd = data
            if not even:
                data_even = data_odd
        else:
            data_even = data
        return data_even

    def __get_key(self, data_dict, filetag, elm_class):
        if elm_class == None:
            key = [x for x in data_dict if x.startswith('{}-'.format(filetag))][0]
        else:
            key = [x for x in data_dict if x.startswith('{}-{}-'.format(elm_class, filetag))][0]
        return key

    def __get_paths(self, simulation_settings):
        path_seperate = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                                     "Exports", simulation_settings["Active Scenario"], "Plots")
        path_single = os.path.join(simulation_settings["Project Path"], simulation_settings["Active Project"],
                                   "Exports", simulation_settings["Active Scenario"], "Scenario Comparison Plots")
        return path_seperate, path_single

    def save_file(self, figure, path, scenario, plot_type, extension):
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        figpath = '{}\{}-{}-XY.{}'.format(path, scenario, plot_type, extension)
        figure.savefig(figpath)
        plt.close(figure)
        print("File saved: {}".format(figpath))
        return


    def multivariateGrid(self, col_x, col_y, col_k, df, k_is_color=False, scatter_alpha=.1, kind="scatter"):
        from matplotlib.lines import Line2D

        def colored_scatter(x, y, c=None):
            def scatter(*args, **kwargs):
                args = (x, y)
                if c is not None:
                    kwargs['c'] = c
                kwargs['alpha'] = scatter_alpha
                plt.scatter(*args, **kwargs)
            return scatter

        def colored_contour(x, y,  c=None):
            def contourf(*args, **kwargs):
                sbn.kdeplot(x, y, shade=True, shade_lowest=False)
                if c is not None:
                    kwargs['c'] = c
                kwargs['alpha'] = scatter_alpha
            return contourf

        g = sbn.JointGrid(
            x=col_x,
            y=col_y,
            data=df,
        )
        legends = []
        custom_lines = []
        colors =plt.cm.tab10.colors

        c = 0
        for name, df_group in df.groupby(col_k):
            if k_is_color:
                color = name
            legends.append(name)
            custom_lines.append(Line2D([0], [0], color=colors[c], lw=4))

            g.plot_joint(
                colored_contour(df_group[col_x], df_group[col_y], colors[c]) if kind == 'kde' else
                colored_scatter(df_group[col_x], df_group[col_y], colors[c]),
            )
            sbn.distplot(
                df_group[col_x].values,
                ax=g.ax_marg_x,
                color=colors[c],
            )
            sbn.distplot(
                df_group[col_y].values,
                ax=g.ax_marg_y,
                color=colors[c],
                vertical=True
            )
            c += 1

        plt.legend(custom_lines, legends)


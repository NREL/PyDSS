import pandas as pd
import os

class Plot:

    def __init__(self, visualization_args, simulation_results):
        print(simulation_results)
        self.simulation_results_dict = simulation_results
        self.visualization_args = visualization_args

        if visualization_args['Voltage_PDF']:
            self.__create_voltage_pdf_plot(visualization_args, simulation_results)
        #print(self.simulation_results_dict)
        return

    def __create_voltage_pdf_plot(self, visualization_args, simulation_results):
        width = visualization_args['Global_width'] if visualization_args['Global_override'] else  \
            visualization_args['Voltage_PDF_settings']['Width']
        height = visualization_args['Global_height'] if visualization_args['Global_override'] else \
            visualization_args['Voltage_PDF_settings']['Height']
        dpi = visualization_args['Global_DPI'] if visualization_args['Global_override'] else \
            visualization_args['Voltage_PDF_settings']['DPI']

        for simulation_key, result in simulation_results.items():
            print(result)

        return
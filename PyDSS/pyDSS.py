import subprocess
import pathlib
import PyDSS
import toml
import os

from PyDSS.pyAnalyzer.dssSimulationResult import ResultObject
from PyDSS.pyAnalyzer.dssGraphicsGenerator import CreatePlots
from PyDSS import dssInstance
from PyDSS.utils.utils import load_data

__author__ = "Aadil Latif"
__copyright__ = """
    BSD 3-Clause License

    Copyright (c) 2018, Alliance for Sustainable Energy LLC, All rights reserved.

    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the 
    following conditions are met:
    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following
    disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the 
    following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote 
    products derived from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
    WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE 
    USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
"""
__license__ = "BSD 3-Clause License"
__version__ = "0.0.1"
__maintainer__ = "Aadil Latif"
__email__ = "aadil.latif@nrel.gov, aadil.latif@gmail.com"
__status__ = "Production"


PYDSS_BASE_DIR = os.path.join(os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS")


class instance(object):

    valid_settings = {
            'Log Results': {'type': bool, 'Options': [True, False]},
            'Return Results': {'type': bool, 'Options': [True, False]},
            'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
            'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},
            'Export Format': {'type': str, 'Options': ["csv", "feather"]},
            'Export Compression': {'type': bool, 'Options': [True, False]},

            'Create dynamic plots': {'type': bool, 'Options': [True, False]},
            'Open plots in browser': {'type': bool, 'Options': [True, False]},

            'Project Path': {'type': str},
            'Start Year': {'type': int, 'Options': range(1970, 2099)},
            'Start Day': {'type': int, 'Options': range(0, 365)},
            'Start Time (min)': {'type': float, 'Options': range(0, 1440)},
            'End Day': {'type': int, 'Options': range(0, 365)},
            'End Time (min)': {'type': float, 'Options': range(0, 1440)},
            'Date offset': {'type': int, 'Options': range(0, 365)},
            'Step resolution (sec)' : {'type': float},
            'Max Control Iterations' : {'type': int},
            'Error tolerance': {'type': float},
            'Simulation Type': {'type': str, 'Options': ["QSTS", "Dynamic", "Snapshot", "Monte Carlo"]},
            'Active Project': {'type': str},
            'Active Scenario': {'type': str},
            'DSS File': {'type': str},

            'Post processing script': {'type': str},
            "Run each iteration": {'type': bool, 'Options': [True, False]},

            'Co-simulation Mode': {'type': bool, 'Options': [True, False]},
            'Federate name': {'type': str},
            'Time delta': {'type': float},
            'Core type': {'type': str},
            'Uninterruptible': {'type': bool, 'Options': [True, False]},
            'Helics logging level': {'type': int, 'Options': range(0, 10)},


            'Logging Level': {'type': str, 'Options': ["DEBUG", "INFO", "WARNING" , "ERROR"]},
            'Log to external file': {'type': bool, 'Options': [True, False]},
            'Display on screen': {'type': bool, 'Options': [True, False]},
            'Clear old log file': {'type': bool, 'Options': [True, False]},

            'Control mode': {'type': str, 'Options': ["Static", "Time"]},
            'Disable PyDSS controllers': {'type': bool, 'Options': [True, False]},

            'Enable frequency sweep': {'type': bool, 'Options': [True, False]},
            'Fundamental frequency': {'type': int, 'Options': [50, 60]},
            'Start frequency': {'type': float},
            'End frequency': {'type': float},
            'frequency increment': {'type': float},
            'Neglect shunt admittance': {'type': bool, 'Options': [True, False]},
            'Percentage load in series': {'type': float, 'Options': range(0, 100)},

            'Number of Monte Carlo scenarios': {'type': int},
    }

    def update_results_dict(self, results_container, args, results):
        results_container['{}-{}-{}-{}-{}'.format(
            args["Active Project"],
            args["Active Scenario"],
            args["Start Year"],
            args["Start Day"],
            args["End Day"],
        )] = (args, results)
        return results_container


    def run(self, simulation_config, scenario):
        path = os.path.dirname(PyDSS.__file__)
        default_vis_settings = load_data(os.path.join(path, 'default_plot_settings.toml'))

        if scenario.plots is not None:
            updated_vis_settings = {**default_vis_settings, **scenario.plots}
        else:
            updated_vis_settings = default_vis_settings

        bokeh_server_proc = None
        if updated_vis_settings['Simulations']['Run_bokeh_server']:
            bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)

        SimulationResults = {}
        args, results = self.__run_scenario(simulation_config,
                                            updated_vis_settings['Simulations']['Run_simulations'],
                                            updated_vis_settings['Simulations']['Generate_visuals'])
        if results is not None:
            SimulationResults = self.update_results_dict(SimulationResults, args, results)

        if updated_vis_settings['Simulations']['Generate_visuals']:
            CreatePlots(updated_vis_settings, SimulationResults)
        if updated_vis_settings['Simulations']['Run_bokeh_server']:
            bokeh_server_proc.terminate()
        print('end of update_results_dict')
        return

    def update_scenario_settings(self, simulation_config):
        path = os.path.dirname(PyDSS.__file__)
        default_sim_settings = load_data(os.path.join(path, 'default_simulation_settings.toml'))
        dss_args = {**default_sim_settings, **simulation_config}
        self.__validate_settings(dss_args)
        return dss_args

    def create_dss_instance(self, dss_args):
        dss = dssInstance.OpenDSS(**dss_args)
        return dss

    def __run_scenario(self, simulation_config, run_simulation=True, generate_visuals=False):
        dss_args = self.update_scenario_settings(simulation_config)
        # TODO: we should serialize the actual simulation config to a file. 
        if run_simulation:
            dss = dssInstance.OpenDSS(**dss_args)
            print('Running scenario: {}'.format(dss_args["Active Scenario"]))
            if dss_args["Number of Monte Carlo scenarios"] > 0:
                dss.RunMCsimulation(samples=dss_args['Number of Monte Carlo scenarios'])
            else:
                dss.RunSimulation()
            del dss
            print(dss)
        if generate_visuals:
            result = ResultObject(os.path.join(
                dss_args['Project Path'],
                dss_args["Active Project"],
                'Exports',
                dss_args['Active Scenario']
            ))
        else:
            result = None
        return dss_args, result


    def __validate_settings(self, dss_args):
        valid_settings = self.valid_settings
        for key, ctype in dss_args.items():
            assert (key in self.valid_settings), "'{}' is not a valid PyDSS argument".format(key)
            assert (isinstance(ctype, valid_settings[key]['type'])), "'{}' can only be a '{}' data type. Was passed {}".format(
                key, valid_settings[key]['type'], type(ctype)
            )
            if 'Options' in valid_settings[key]:
                if isinstance(valid_settings[key]['Options'], list):
                    assert (ctype in  (valid_settings[key]['Options'])),\
                        "Invalid argument value '{}'. Possible values are: {}".format(ctype ,valid_settings[key]['Options'])
                elif isinstance(valid_settings[key]['Options'], range):
                    assert (min(valid_settings[key]['Options']) <= ctype <= max(valid_settings[key]['Options'])), \
                        "Value '{}' out of bounds for '{}'. Allowable range is: {}-{}".format(
                            ctype,
                            key,
                            min(valid_settings[key]['Options']),
                            max(valid_settings[key]['Options'])
                        )

        for key, ctype in valid_settings.items():
            assert (key in dss_args), "'{}' definition is missing in the TOML file".format(key)

        assert (dss_args['End frequency'] >= dss_args['Start frequency']),\
            "'End frequency' can not be smaller than 'Start frequency'"
        assert (dss_args['End Day'] >= dss_args['Start Day']), \
            "'End day' can not be smaller than 'Start day'"
        assert (os.path.exists(dss_args['Project Path'])), \
            "Project path {} does not exist.".format(dss_args['Project Path'])
        assert (os.path.exists(os.path.join(dss_args['Project Path'], dss_args["Active Project"]))), \
            "Project '{}' does not exist.".format(dss_args["Active Project"])

        assert (os.path.exists(os.path.join(dss_args['Project Path'],
                                            dss_args["Active Project"],
                                            'Scenarios',
                                            dss_args['Active Scenario']))), \
            "Scenario '{}' does not exist.".format( dss_args['Active Scenario'])

        assert (os.path.exists(os.path.join(dss_args['Project Path'],
                                            dss_args["Active Project"],
                                            'DSSfiles',
                                            dss_args['DSS File']))), \
            "Master DSS file '{}' does not exist.".format(dss_args['DSS File'])
        return

if __name__ == '__main__':
    a = instance()
    #a.run(f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/base_case.toml')
    #a.run(f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/self_consumption.toml')
    #a.run(f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/volt_var.toml')
    #a.run(f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/multiple_controllers.toml')

    a.run([f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/base_case.toml',
           f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/self_consumption.toml',
           f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/volt_var.toml',
           f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/multiple_controllers.toml'],
           f'{PYDSS_BASE_DIR}/examples/Custom_controls_example/Scenarios/automated_comparison.toml')

    # a.run('f{PYDSS_BASE_DIR}/examples/Dynamic_visualization_example/Scenarios/Dynamic_visuals.toml',
    #       'f{PYDSS_BASE_DIR}/examples/Dynamic_visualization_example/Scenarios/user_defined_vis_settings.toml')

    # a.run('f{PYDSS_BASE_DIR}/examples/Harmonics_examples/Scenarios/freq_scan_qsts.toml',
    #       'f{PYDSS_BASE_DIR}/examples/Harmonics_examples/Scenarios/Freq_scan_qsts_visuals.toml')

    #a.run('f{PYDSS_BASE_DIR}/examples/Monte_carlo_examples/Scenarios/monte_carlo_settings.toml')

    del a

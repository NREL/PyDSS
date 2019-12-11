from PyDSS.pyAnalyzer.dssSimulationResult import ResultObject
from PyDSS.pyAnalyzer.dssGraphicsGenerator import CreatePlots
from PyDSS import dssInstance
import subprocess
import pathlib
import PyDSS
import toml
import os


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

class instance(object):

    valid_settings = {
            'Log Results': {'type': bool, 'Options': [True, False]},
            'Return Results': {'type': bool, 'Options': [True, False]},
            'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
            'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},

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

    def __init__(self):
        return

    def create_new_project(self, base_path, project_name, scenario_name):
        logs = os.path.join(base_path, project_name, 'Logs')
        exports = os.path.join(base_path, project_name, 'Exports')
        dssfiles = os.path.join(base_path, project_name, 'DSSfiles')
        scenario = os.path.join(base_path, project_name, 'PyDSS Scenarios', scenario_name)

        pathlib.Path(logs).mkdir(parents=True, exist_ok=True)
        pathlib.Path(exports).mkdir(parents=True, exist_ok=True)
        pathlib.Path(dssfiles).mkdir(parents=True, exist_ok=True)
        pathlib.Path(scenario).mkdir(parents=True, exist_ok=True)

        self.create_scenario_template(scenario)
        return

    def create_scenario_template(self, scenario_path, base_path=None, project_name=None):
        #TODO: once xlxs inputs changed to xlm or json
        return

    def read_toml_file(self, filename):
        settings_text = ''
        f = open(filename, "r")
        text = settings_text.join(f.readlines())
        toml_data = toml.loads(text)
        f.close()
        return toml_data

    def update_results_dict(self, results_container, args, results):
        results_container['{}-{}-{}-{}-{}'.format(
            args["Active Project"],
            args["Active Scenario"],
            args["Start Year"],
            args["Start Day"],
            args["End Day"],
        )] = (args, results)
        return results_container


    def run(self, simulation_file, vis_settings_file=None):
        path = os.path.dirname(PyDSS.__file__)
        default_vis_settings = self.read_toml_file(os.path.join(path, 'default_plot_settings.toml'))

        if vis_settings_file != None:
            vis_settings = self.read_toml_file(vis_settings_file)
            updated_vis_settings = {**default_vis_settings, **vis_settings}
        else:
            updated_vis_settings = default_vis_settings

        bokeh_server_proc = None
        if updated_vis_settings['Simulations']['Run_bokeh_server']:
            bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)

        SimulationResults = {}
        if isinstance(simulation_file, str):
            args, results = self.__run_scenario(simulation_file,
                                                updated_vis_settings['Simulations']['Run_simulations'],
                                                updated_vis_settings['Simulations']['Generate_visuals'])
            if results is not None:
                SimulationResults = self.update_results_dict(SimulationResults, args, results)


        elif isinstance(simulation_file, list):
            for sim_file in simulation_file:
                args, results = self.__run_scenario(sim_file,
                                                    updated_vis_settings['Simulations']['Run_simulations'],
                                                    updated_vis_settings['Simulations']['Generate_visuals'])
                SimulationResults = self.update_results_dict(SimulationResults, args, results)

        if updated_vis_settings['Simulations']['Generate_visuals']:
            CreatePlots(updated_vis_settings, SimulationResults)
        if updated_vis_settings['Simulations']['Run_bokeh_server']:
            bokeh_server_proc.terminate()
        print('end of update_results_dict')
        return

    def update_scenario_settigs(self, Scenario_TOML_file_path):
        path = os.path.dirname(PyDSS.__file__)
        default_sim_settings = self.read_toml_file(os.path.join(path, 'default_simulation_settings.toml'))
        sim_settings = self.read_toml_file(Scenario_TOML_file_path)
        dss_args = {**default_sim_settings, **sim_settings}
        self.__validate_settings(dss_args)
        return dss_args

    def create_dss_instance(self, dss_args):
        dss = dssInstance.OpenDSS(**dss_args)
        return dss

    def __run_scenario(self, Scenario_TOML_file_path, run_simulation=True, generate_visuals=False):
        dss_args = self.update_scenario_settigs(Scenario_TOML_file_path)
        if run_simulation:
            dss = dssInstance.OpenDSS(**dss_args)
            print('Running scenario: {}'.format(Scenario_TOML_file_path))
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
                                            'PyDSS Scenarios',
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
    #a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\base_case.toml')
    #a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\self_consumption.toml')
    #a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\volt_var.toml')
    #a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\multiple_controllers.toml')

    a.run([r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\base_case.toml',
           r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\self_consumption.toml',
           r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\volt_var.toml',
           r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\multiple_controllers.toml'],
          r'C:\Users\alatif\Desktop\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\automated_comparison.toml')

    # a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Dynamic_visualization_example\PyDSS Scenarios\Dynamic_visuals.toml',
    #       r'C:\Users\alatif\Desktop\PyDSS\examples\Dynamic_visualization_example\PyDSS Scenarios\user_defined_vis_settings.toml')

    # a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Harmonics_examples\PyDSS Scenarios\freq_scan_qsts.toml',
    #       r'C:\Users\alatif\Desktop\PyDSS\examples\Harmonics_examples\PyDSS Scenarios\Freq_scan_qsts_visuals.toml')

    #a.run(r'C:\Users\alatif\Desktop\PyDSS\examples\Monte_carlo_examples\PyDSS Scenarios\monte_carlo_settings.toml')

    del a
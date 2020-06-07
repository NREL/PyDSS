import subprocess
import pathlib
import PyDSS
import toml
import os
import logging

from PyDSS.exceptions import InvalidConfiguration
from PyDSS import dssInstance
from PyDSS.utils.utils import dump_data, load_data

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


logger = logging.getLogger(__name__)


class instance(object):

    valid_settings = {
        "Exports": {
            'Export Mode': {'type': str, 'Options': ["byClass", "byElement"]},
            'Export Style': {'type': str, 'Options': ["Single file", "Separate files"]},
            # Feather is not supported because its underlying libraries do not support complex numbers
            'Export Format': {'type': str, 'Options': ["csv", "h5"]},
            'Export Compression': {'type': bool, 'Options': [True, False]},
            'Export Iteration Order': {'type': str, 'Options': ["ElementValuesPerProperty",
                                                                "ValuesByPropertyAcrossElements"]},
            'Export Elements': {'type': bool, 'Options': [True, False]},
            'Export Event Log': {'type': bool, 'Options': [True, False]},
            'Export Data Tables': {'type': bool, 'Options': [True, False]},
            'Export Data In Memory': {'type': bool, 'Options': [True, False]},
            'Export PV Profiles': {'type': bool, 'Options': [True, False]},
            'HDF Max Chunk Bytes': {'type': int, 'Options': range(16 * 1024, 1024 * 1024 + 1)},
            'Log Results': {'type': bool, 'Options': [True, False]},
            'Result Container': {'type': str, 'Options': ['ResultContainer', 'ResultData']},
        },
        "Frequency": {
            'Enable frequency sweep': {'type': bool, 'Options': [True, False]},
            'Fundamental frequency': {'type': int, 'Options': [50, 60]},
            'Start frequency': {'type': float},
            'End frequency': {'type': float},
            'frequency increment': {'type': float},
            'Neglect shunt admittance': {'type': bool, 'Options': [True, False]},
            'Percentage load in series': {'type': float, 'Options': range(0, 100)},
        },
        "Helics": {
            'Co-simulation Mode': {'type': bool, 'Options': [True, False]},
            'Iterative Mode': {'type': bool, 'Options': [True, False]},
            'Max co-iterations': {'type': int, 'Options': range(1, 1000)},
            'Error tolerance': {'type': float},
            'Federate name': {'type': str},
            'Broker': {'type': str},
            'Broker port': {'type': int},
            'Time delta': {'type': float},
            'Core type': {'type': str},
            'Uninterruptible': {'type': bool, 'Options': [True, False]},
            'Helics logging level': {'type': int, 'Options': range(0, 10)},
        },
        "Logging": {
            'Logging Level': {'type': str, 'Options': ["DEBUG", "INFO", "WARNING" , "ERROR"]},
            'Log to external file': {'type': bool, 'Options': [True, False]},
            'Display on screen': {'type': bool, 'Options': [True, False]},
            'Clear old log file': {'type': bool, 'Options': [True, False]},
            'Pre-configured logging': {'type': bool, 'Options': [True, False]},
        },
        "MonteCarlo": {
            'Number of Monte Carlo scenarios': {'type': int},
        },
        "Plots": {
            'Create dynamic plots': {'type': bool, 'Options': [True, False]},
            'Open plots in browser': {'type': bool, 'Options': [True, False]},
        },
        "Project": {
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
            'Scenarios': {'type': list},
            'Active Scenario': {'type': str},
            'DSS File': {'type': str},
            'DSS File Absolute Path': {'type': bool, 'Options': [True, False]},
            'Return Results': {'type': bool, 'Options': [True, False]},
            'Control mode': {'type': str, 'Options': ["Static", "Time"]},
            'Disable PyDSS controllers': {'type': bool, 'Options': [True, False]},
        },
        "Reports": {
            'Format': {'type': str, 'Options': ["csv", "h5"]},
            'Types': {'type': list}
        },
    }

    def __init__(self):
        self._estimated_space = None

    def run(self, simulation_config, project, scenario, dry_run=False):
        bokeh_server_proc = None
        if simulation_config['Plots']['Create dynamic plots']:
            bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
        try:
            self.run_scenario(
                project,
                scenario,
                simulation_config,
                dry_run=dry_run,
            )
        finally:
            if simulation_config['Plots']['Create dynamic plots']:
                bokeh_server_proc.terminate()

        return

    def update_scenario_settings(self, simulation_config):
        path = os.path.dirname(PyDSS.__file__)
        dss_args = load_data(os.path.join(path, 'defaults', 'simulation.toml'))
        for category, params in dss_args.items():
            if category in simulation_config:
                params.update(simulation_config[category])
        self.__validate_settings(dss_args)
        return dss_args

    def create_dss_instance(self, dss_args):
        dss = dssInstance.OpenDSS(dss_args)
        return dss

    def run_scenario(self, project, scenario, simulation_config , dry_run=False):
        dss_args = self.update_scenario_settings(simulation_config)
        self._dump_scenario_simulation_settings(dss_args)
        
        if dry_run:
            dss = dssInstance.OpenDSS(dss_args)
            logger.info('Dry run scenario: %s', dss_args["Project"]["Active Scenario"])
            if dss_args["MonteCarlo"]["Number of Monte Carlo scenarios"] > 0:
                raise InvalidConfiguration("Dry run does not support MonteCarlo simulation.")
            else:
                self._estimated_space = dss.DryRunSimulation(project, scenario)
            return None, None
        
        dss = dssInstance.OpenDSS(dss_args)
        logger.info('Running scenario: %s', dss_args["Project"]["Active Scenario"])
        if dss_args["MonteCarlo"]["Number of Monte Carlo scenarios"] > 0:
            dss.RunMCsimulation(project, scenario, samples=dss_args["MonteCarlo"]['Number of Monte Carlo scenarios'])
        else:
            dss.RunSimulation(project, scenario)
        return dss_args

    def get_estimated_space(self):
        return self._estimated_space

    def _dump_scenario_simulation_settings(self, dss_args):
        # Various settings may have been updated. Write the actual settings to a file.
        scenario_simulation_filename = os.path.join(
            dss_args["Project"]["Project Path"],
            dss_args["Project"]["Active Project"],
            "Scenarios",
            dss_args["Project"]["Active Scenario"],
            "simulation-run.toml"
        )
        dump_data(dss_args, scenario_simulation_filename)

    def __validate_settings(self, dss_args):
        for category, params in dss_args.items():
            valid_settings = self.valid_settings[category]
            for key, ctype in params.items():
                assert (key in valid_settings), "category='{}' field='{}' is not a valid PyDSS argument".format(category, key)
                if valid_settings[key]['type'] == float and isinstance(ctype, int):
                    ctype = float(ctype)
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

        for category, params in self.valid_settings.items():
            for key, ctype in params.items():
                assert (key in dss_args[category]), "category='{}' field='{}' definition is missing in the TOML file".format(category, key)

        assert (dss_args['Frequency']['End frequency'] >= dss_args['Frequency']['Start frequency']),\
            "'End frequency' can not be smaller than 'Start frequency'"
        assert (dss_args['Project']['End Day'] >= dss_args['Project']['Start Day']), \
            "'End day' can not be smaller than 'Start day'"
        assert (os.path.exists(dss_args['Project']['Project Path'])), \
            "Project path {} does not exist.".format(dss_args['Project']['Project Path'])
        assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'], dss_args['Project']["Active Project"]))), \
            "Project '{}' does not exist.".format(dss_args['Project']["Active Project"])

        assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'],
                                            dss_args['Project']["Active Project"],
                                            'Scenarios',
                                            dss_args['Project']['Active Scenario']))), \
            "Scenario '{}' does not exist.".format( dss_args['Project']['Active Scenario'])
        assert (os.path.exists(os.path.join(dss_args['Project']['Project Path'],
                                            dss_args['Project']["Active Project"],
                                            'DSSfiles',
                                            dss_args['Project']['DSS File']))), \
            "Master DSS file '{}' does not exist.".format(dss_args['Project']['DSS File'])

        if "Reports" in dss_args:
            if [x for x in dss_args["Reports"]["Types"] if x["enabled"]]:
                if not dss_args["Exports"]["Log Results"]:
                    raise InvalidConfiguration("Reports are only supported with Log Results")
                if dss_args["Exports"]["Result Container"] != "ResultData":
                    raise InvalidConfiguration("Reports are only supported with ResultData container")
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
    a.run(
        r'C:\Users\ajain\Desktop\PyDSS_develop_branch\PyDSS\examples\Custom_controls_example\PyDSS Scenarios\base_case.toml')
    del a

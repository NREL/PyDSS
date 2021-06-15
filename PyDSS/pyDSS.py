import subprocess
import pathlib
import PyDSS
import toml
import os
import logging

from PyDSS.exceptions import InvalidConfiguration
from PyDSS import dssInstance
from PyDSS.utils.utils import dump_data, load_data
from PyDSS.valiate_settings import validate_settings

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
__version__ = "2.0.1"
__maintainer__ = "Aadil Latif"
__email__ = "aadil.latif@nrel.gov, aadil.latif@gmail.com"
__status__ = "Production"

PYDSS_BASE_DIR = os.path.join(os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS")

logger = logging.getLogger(__name__)


class instance(object):

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
        validate_settings(dss_args)
        return dss_args

    def create_dss_instance(self, dss_args):
        dss = dssInstance.OpenDSS(dss_args)
        #dss.init(dss_args)
        return dss

    def run_scenario(self, project, scenario, simulation_config, dry_run=False):
        dss_args = self.update_scenario_settings(simulation_config)
        self._dump_scenario_simulation_settings(dss_args)

        if dry_run:
            dss = dssInstance.OpenDSS(dss_args)
            #dss.init(dss_args)
            logger.info('Dry run scenario: %s', dss_args["Project"]["Active Scenario"])
            if dss_args["MonteCarlo"]["Number of Monte Carlo scenarios"] > 0:
                raise InvalidConfiguration("Dry run does not support MonteCarlo simulation.")
            else:
                self._estimated_space = dss.DryRunSimulation(project, scenario)
            return None, None

        dss = dssInstance.OpenDSS(dss_args)
        #dss.init(dss_args)
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

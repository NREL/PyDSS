import subprocess
import pathlib
import PyDSS
import toml
import os
import logging

from PyDSS.common import RUN_SIMULATION_FILENAME
from PyDSS.exceptions import InvalidConfiguration
from PyDSS.dssInstance import OpenDSS
from PyDSS.simulation_input_models import SimulationSettingsModel, dump_settings
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
__version__ = "2.0.4"
__maintainer__ = "Aadil Latif"
__email__ = "aadil.latif@nrel.gov, aadil.latif@gmail.com"
__status__ = "Production"

PYDSS_BASE_DIR = os.path.join(os.path.dirname(getattr(PyDSS, "__path__")[0]), "PyDSS")

logger = logging.getLogger(__name__)


class instance(object):

    def __init__(self):
        self._estimated_space = None

    def run(self, settings: SimulationSettingsModel, project, scenario, dry_run=False):
        bokeh_server_proc = None
        if settings.plots.create_dynamic_plots:
            bokeh_server_proc = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
        try:
            self.run_scenario(
                project,
                scenario,
                settings,
                dry_run=dry_run,
            )
        finally:
            if settings.plots.create_dynamic_plots:
                bokeh_server_proc.terminate()

        return

    def create_dss_instance(self, dss_args):
        return OpenDSS(dss_args)

    def run_scenario(self, project, scenario, settings: SimulationSettingsModel, dry_run=False):
        if dry_run:
            dss = OpenDSS(settings)
            self._dump_scenario_simulation_settings(settings)
            #dss.init(dss_args)
            logger.info('Dry run scenario: %s', settings.project.active_scenario)
            if settings.monte_carlo.num_scenarios > 0:
                raise InvalidConfiguration("Dry run does not support MonteCarlo simulation.")
            else:
                self._estimated_space = dss.DryRunSimulation(project, scenario)
            return None, None

        opendss = OpenDSS(settings)
        self._dump_scenario_simulation_settings(settings)
        logger.info('Running scenario: %s', settings.project.active_scenario)
        if settings.monte_carlo.num_scenarios > 0:
            opendss.RunMCsimulation(project, scenario, samples=settings.monte_carlo.num_scenarios)
        else:
            for is_complete, _, _, _ in opendss.RunSimulation(project, scenario):
                if is_complete:
                    break

    def get_estimated_space(self):
        return self._estimated_space

    def _dump_scenario_simulation_settings(self, settings: SimulationSettingsModel):
        # Various settings may have been updated. Write the actual settings to a file.
        scenario_simulation_filename = os.path.join(
            settings.project.project_path,
            settings.project.active_project,
            "Scenarios",
            settings.project.active_scenario,
            RUN_SIMULATION_FILENAME,
        )
        dump_settings(settings, scenario_simulation_filename)

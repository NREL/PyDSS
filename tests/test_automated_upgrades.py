
import os
import shutil
import pytest

from PyDSS.common import RUN_SIMULATION_FILENAME
from PyDSS.pydss_project import PyDssProject
from tests.common import AUTOMATED_UPGRADES_PROJECT_PATH
from PyDSS.common import SIMULATION_SETTINGS_FILENAME

VOLTAGE_UPGRADES_FILES = ['voltage_upgrades.dss', 'Processed_voltage_upgrades.json',
                          'Voltage_violations_comparison.json']
THERMAL_UPGRADE_FILES = ['thermal_upgrades.dss', 'Processed_thermal_upgrades.json',
                         'Thermal_violations_comparison.json', 'summary_of_parallel_line_upgrades.csv',
                         'summary_of_parallel_transformer_upgrades.csv']


@pytest.fixture
def clean_upgrades_results():
    # delete files in Exports directory, logs in 'Logs' directory
    export_path = os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, "Exports")
    logs_path = os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, "Logs")
    simulation_run_file = os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, RUN_SIMULATION_FILENAME)
    store_file = os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'store.h5')

    for path in (logs_path, export_path):
        if os.path.exists(path):
            shutil.rmtree(path)
            os.mkdir(path)
    # delete 'PostProcess' in Scenarios folder
    for f in os.listdir(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios')):
        if os.path.exists(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios', f, 'PostProcess')):
            shutil.rmtree(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios', f, 'PostProcess'))

    if os.path.exists(simulation_run_file):
        os.remove(simulation_run_file)

    if os.path.exists(store_file):
        os.remove(store_file)

    yield

    # delete files in Exports directory, logs in 'Logs' directory
    for path in (logs_path, export_path):
        if os.path.exists(path):
            shutil.rmtree(path)
            os.mkdir(path)
    # create empty file (needed for GIT)
    with open(os.path.join(logs_path, '.keep'), 'w') as fp:
        pass
    with open(os.path.join(export_path, '.keep'), 'w') as fp:
        pass

    # delete 'PostProcess' in Scenarios folder
    for f in os.listdir(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios')):
        if os.path.exists(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios', f, 'PostProcess')):
            shutil.rmtree(os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios', f, 'PostProcess'))

    if os.path.exists(simulation_run_file):
        os.remove(simulation_run_file)

    if os.path.exists(store_file):
        os.remove(store_file)



def test_automated_upgrades_project(clean_upgrades_results):
    project = PyDssProject.load_project(AUTOMATED_UPGRADES_PROJECT_PATH)
    PyDssProject.run_project(
        AUTOMATED_UPGRADES_PROJECT_PATH,
        simulation_file=SIMULATION_SETTINGS_FILENAME,
    )

    path_to_scenarios = os.path.join(AUTOMATED_UPGRADES_PROJECT_PATH, 'Scenarios')
    scenario_names = [d for d in os.listdir(path_to_scenarios) if os.path.isdir(os.path.join(path_to_scenarios, d))]
    assert len(scenario_names) == 2
    assert any('thermal' in scenario.lower() for scenario in scenario_names)
    assert any('voltage' in scenario.lower() for scenario in scenario_names)

    for scenario in scenario_names:
        if 'thermal' in scenario.lower():
            ref_list = THERMAL_UPGRADE_FILES
        elif 'voltage' in scenario.lower():
            ref_list = VOLTAGE_UPGRADES_FILES
        result_path = os.path.join(path_to_scenarios, scenario, 'PostProcess')
        file_list = os.listdir(result_path)
        assert all(x in file_list for x in ref_list)

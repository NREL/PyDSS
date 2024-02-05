from click.testing import CliRunner
from pathlib import Path
import tempfile
import shutil
import toml
import os

from PyDSS.cli.add_scenario import build_scenario

PYDSS_PROJECT = Path(__file__).parent / "data" / "project"
MAPPING_FILE = Path(__file__).parent / "data" / "add_scenario" / "controller_map.toml"

def test_add_scenario():
    
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdirname_obj = Path(tmpdirname)
        shutil.copytree(PYDSS_PROJECT, tmpdirname, dirs_exist_ok=True)
        settings_path = tmpdirname_obj / "simulation.toml"
        settings = toml.load(settings_path)
        settings['Project']['Project Path'] = str(tmpdirname_obj.absolute())
        toml.dump(settings, open(settings_path, "w"))
        
        print(tmpdirname_obj)
        build_scenario(str(tmpdirname), "test_scenario", str(MAPPING_FILE))
        os.system("pause")
        # runner = CliRunner()
        # result = runner.invoke(add_scenario, [str(tmpdirname), "test_scenario", MAPPING_FILE])
        
        
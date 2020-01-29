import click
import sys
import os

@click.command()
@click.option('--pydss_path',
              default=r'C:\Users\ajain\Desktop\PyDSS_develop_branch\PyDSS',
              help='number of greetings')
@click.option('--sim_path',
              default=r'C:\Users\ajain\Desktop\PyDSS_develop_branch\PyDSS\examples\External_interfacing_example\pyDSS_project\PyDSS Scenarios',
              help='number of greetings')
@click.option('--sim_file',
              default=r'helics_interface.toml',
              help='number of greetings')
def run_pyDSS(pydss_path, sim_path, sim_file):
    print(pydss_path, sim_path, sim_file)
    sys.path.append(pydss_path)
    sys.path.append(os.path.join(pydss_path, 'PyDSS'))
    from pyDSS import instance as dssInstance
    a = dssInstance()
    a.run(os.path.join(sim_path, sim_file))

run_pyDSS()



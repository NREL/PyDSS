import click
import sys
import os

@click.command()
@click.option('--pydss_path',
              default=r'C:\Users\alatif\Desktop\PyDSS')
@click.option('--sim_path',
              default=r'C:\Users\alatif\Desktop\PyDSS\examples\External_interfacing_example\pyDSS_project\PyDSS Scenarios')
@click.option('--sim_file',
              default=r'api_interface.toml')
@click.option('--run_simulation',
              default=True)
@click.option('--generate_visuals',
              default=False)
def run_pyDSS(pydss_path, sim_path, sim_file, run_simulation, generate_visuals):
    sys.path.append(pydss_path)
    sys.path.append(os.path.join(pydss_path, 'PyDSS'))
    from pyDSS import instance as dssInstance
    a = dssInstance()
    sim_args = a.update_scenario_settigs(os.path.join(sim_path, sim_file))
    dssInstance = a.create_dss_instance(sim_args)
    for t in range(5):
        x = {'Load.mpx000635970':{'kW':7.28}}
        results = dssInstance.RunStep(t, x)
        print(results['Load.mpx000635970']['Powers']['E']['value'])
    dssInstance.ResultContainer.ExportResults()
    dssInstance.DeleteInstance()
    del a
run_pyDSS()



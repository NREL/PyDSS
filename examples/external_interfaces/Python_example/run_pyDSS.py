import click
import toml
import sys
import os

@click.command()
@click.option('--pydss_path',
              default=r'C:\Users\alatif\Desktop\PyDSS_2.0\PyDSS')
@click.option('--sim_path',
              default=r'C:\Users\alatif\Desktop\PyDSS_2.0\PyDSS\examples\external_interfaces\Python_example')
@click.option('--sim_file',
              default=r'simulation.toml')
def run_pyDSS(pydss_path, sim_path, sim_file):
    sys.path.append(pydss_path)
    sys.path.append(os.path.join(pydss_path, 'PyDSS'))
    file1 = open(os.path.join(sim_path, sim_file),"r")
    text = file1.read()
    sim_args = toml.loads(text)
    from pyDSS import instance as dssInstance
    a = dssInstance()
    dssInstance = a.create_dss_instance(sim_args)
    for t in range(5):
        x = {'Load.mpx000635970':{'kW':7.28}}
        results = dssInstance.RunStep(t, x)
        print(results['Load.mpx000635970']['Powers']['E']['value'])
    dssInstance.ResultContainer.ExportResults()
    dssInstance.DeleteInstance()
    del a
run_pyDSS()



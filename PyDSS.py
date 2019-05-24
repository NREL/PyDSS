from PyDSS import dssInstance
import logging
import click
import os

@click.command()
# Settings for exporting results
@click.option('--log_results', default=True, type=click.BOOL, help='Set true if results need to be exported')
@click.option('--return_results', default=False, type=click.BOOL,
              help='Set true to access results after every iteration')
@click.option('--export_mode', default='byClass', type=click.STRING, help='possible options "byClass" and "byElement"')
@click.option('--export_style', default='Single file', type=click.STRING,
              help='possible options "Single_file" and "Separate_files"')
# Plot Settings
@click.option('--create_dynamic_plots', default=True, type=click.BOOL, help='render dynamic plot using bokeh')

# Simulation Settings
@click.option('--start_year', default=2017, type=click.INT, help='Start year for the simulation study')
@click.option('--start_day', default=1, type=click.INT, help='Start day for the simulation study')  # 156-163, 286-293
@click.option('--end_day', default=3, type=click.INT, help='End day for the simulation study')
@click.option('--date_offset', default=1, type=click.INT, help='Date offset to be added')
@click.option('--step_resolution_min', default=30, type=click.FLOAT, help='Time step resolution in minutes')
@click.option('--max_control_iterations', default=15, type=click.INT, help='Maximum outer loop control iterations')
@click.option('--error_tolerance', default=0.001, type=click.FLOAT, help='Error tolerance in per unit')
@click.option('--simulation_type', default='Daily', type=click.STRING, help='possible modes "Daily" and "Snapshot"')
@click.option('--active_project', default='BRPL', type=click.STRING, help='Name of project to run')
@click.option('--active_scenario', default='peak_shaving', type=click.STRING, help='Project scenario to use')
@click.option('--dss_file', default='Darbi_1.dss', type=click.STRING,
              help='The main OpenDSS file')
# Logger settings
@click.option('--logging_level', default='DEBUG', type=click.STRING, help='possible options "DEBUG" and "INFO"')
@click.option('--log_to_external_file', default=False, type=click.BOOL, help='Boolean variable ')
@click.option('--display_on_screen', default=True, type=click.BOOL, help='Boolean variable')
@click.option('--clear_old_log_file', default=True, type=click.BOOL, help='Boolean variable')

def RunSimulation(**kwargs):
    dss_args = {
        # Settings for exporting results
        'Log Results': kwargs.get('log_results'),
        'Return Results': kwargs.get('return_results'),
        'Export Mode': kwargs.get('export_mode'),
        'Export Style': kwargs.get('export_style').replace('_', ' '),

        # Plot Settings
        'Create dynamic plots': kwargs.get('create_dynamic_plots'),

        # Simulation Settings
        'Project Path': r'C:\Users\alatif\Desktop\PyDSS-Projects',
        'Start Year': kwargs.get('start_year'),
        'Start Day': kwargs.get('start_day'),
        'End Day': kwargs.get('end_day'),
        'Date offset' : kwargs.get('date_offset'),
        'Step resolution (min)': kwargs.get('step_resolution_min'),
        'Max Control Iterations': kwargs.get('max_control_iterations'),
        'Error tolerance': kwargs.get('error_tolerance'),
        'Simulation Type': kwargs.get('simulation_type'),
        'Active Project': kwargs.get('active_project'),
        'Active Scenario': kwargs.get('active_scenario'),
        'DSS File': kwargs.get('dss_file'),
        'Open plots in browser': True,

        # Logger settings
        'Logging Level': logging.DEBUG if kwargs.get('logging_level') == 'DEBUG' else logging.INFO,
        'Log to external file': kwargs.get('log_to_external_file'),
        'Display on screen': kwargs.get('display_on_screen'),
        'Clear old log file': kwargs.get('clear_old_log_file'),
    }
    import subprocess
    BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
    dss = dssInstance.OpenDSS(**dss_args)
    #
    #dss.CreateGraph(Visualize=True)
    dss.RunSimulation()
  #  BokehServer.terminate()
    # DSS.RunMCsimulation(MCscenarios = 3)
    #dss.DeleteInstance()
    os.system('pause')
    del dss

if __name__ == '__main__':
    RunSimulation()
    print('End')
    # process(sys.argv[3:])


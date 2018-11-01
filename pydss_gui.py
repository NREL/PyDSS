# from PyQt5.uic.Compiler.qtproxies import i18n_string
import PyDSS.dssInstance as dssInstance
import subprocess
import logging

# import os

dssArgs = {
    # Settings for exporting results
    'Log Results': True,
    'Return Results': True,
    'Export Mode': 'byClass',  # 'byClass'        , 'byElement'
    'Export Style': 'Single file',  # 'Separate files' , 'Single file'

    # Plot Settings
    'Network layout': False,
    'Time series': False,
    'XY plot': False,
    'Sag plot': False,
    'Histogram': False,
    'GIS overlay': False,

    # Simulation Settings
    'Start Day': 157,  # 156, 286
    'End Day': 158,  # 163, 293
    'Step resolution (min)': 1,
    'Max Control Iterations': 10,
    'Simulation Type': 'Daily',
    'Active Project': 'SRP',
    'Active Scenario': 'Legacy',
    'DSS File': 'SRP_test_network.dss',
    'Error tolerance': 0.005,

    # Logger settings
    'Logging Level': logging.DEBUG,
    'Log to external file': True,
    'Display on screen': True,
    'Clear old log file': True,
}

BokehServer = subprocess.Popen(["bokeh", "serve"], stdout=subprocess.PIPE)
DSS = dssInstance.OpenDSS(**dssArgs)
DSS.RunSimulation()
BokehServer.terminate()
DSS.DeleteInstance()

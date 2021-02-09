"""
CLI to run the PyDSS server
"""

from PyDSS.api.server import pydss_server
#from aiohttp import web
import logging
import click
import PyDSS
import os

logger = logging.getLogger(__name__)


@click.option(
    "-l", "--log-config",
    default="api/logging.yaml",
    show_default=True,
    help="Path to the logger settings file",
)

@click.option(
    "-e", "--endpoints-file",
    default="api/endpoints.yaml",
    show_default=True,
    help="Path to the end points info file"
)

@click.option(
    "-c", "--config-file",
    default="api/src/config.yaml",
    show_default=True,
    help="Path to the config file"
)

@click.command()
def serve(log_config, endpoints_file, config_file):
    from pathlib import Path
    basePath = PyDSS.__path__[0]
    config_file = os.path.join(basePath, config_file)
    log_config = os.path.join(basePath, log_config)
    endpoints_file = os.path.join(basePath, endpoints_file)

    """Run a PyDSS RESTful API server."""
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    args = {
        "config_file" : config_file,
        "log_config" : log_config,
        "endpoints_file" : endpoints_file,
    }
    pydss = pydss_server(debug=True, **args)
    #web.run_app(pydss.app, port=port)



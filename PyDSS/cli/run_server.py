"""
CLI to run the pydss server
"""

from loguru import logger
from aiohttp import web
import click

from pydss.api.server import pydss_server

@click.option(
    "-p", "--port",
    default=9090,
    show_default=True,
    help="Socket port for the server",
)

@click.command()
def serve(ip="127.0.0.1",port=9090):
    """Run a pydss RESTful API server."""
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.level("DEBUG")
    pydss = pydss_server(ip, port)
    web.run_app(pydss.app, port=port)
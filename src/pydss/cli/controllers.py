"""
CLI to add controllers to the local registry
"""

import sys
import os

import click


from pydss.common import CONTROLLER_TYPES
from pydss.utils.utils import load_data
from pydss.registry import Registry

@click.group()
def controllers():
    """Manage registered pydss controllers."""


@click.argument("filename")
@click.argument("controller_type")
@click.command()
def register(controller_type, filename):
    """Register a controller in the local registry."""
    if controller_type not in CONTROLLER_TYPES:
        print(f"controller_type must be one of {CONTROLLER_TYPES}")
        sys.exit(1)
    if not os.path.exists(filename):
        print(f"{filename} does not exist")
        sys.exit(1)

    registry = Registry()
    for name in load_data(filename):
        data = {"name": name, "filename": filename}
        registry.register_controller(controller_type, data)
        print(f"Registered {controller_type} {name}")


@click.argument("name")
@click.argument("controller_type")
@click.command()
def unregister(controller_type, name):
    """Unregister a controller."""
    Registry().unregister_controller(controller_type, name)
    print(f"Unregistered {controller_type} {name}")


@click.command()
def show():
    """Show the registered controllers."""
    Registry().show_controllers()


@click.command()
def reset_defaults():
    """Reset defaults."""
    Registry().reset_defaults(controllers_only=True)
    print("Reset pydss defaults")


controllers.add_command(register)
controllers.add_command(unregister)
controllers.add_command(show)
controllers.add_command(reset_defaults)

"""Test registry."""

import os
import tempfile

import pytest

from PyDSS.common import ControllerType, CONTROLLER_TYPES
from PyDSS.registry import Registry, DEFAULT_REGISTRY


# Don't change the user's registry.
TEST_FILENAME = os.path.join("tests", "pydss_test_registry.json")
CTYPE = ControllerType.PV_CONTROLLER.value


@pytest.fixture
def registry_fixture():
    yield
    if os.path.exists(TEST_FILENAME):
        os.remove(TEST_FILENAME)


def clear_controllers(registry):
    for controller_type in CONTROLLER_TYPES:
        for controller in registry.list_controllers(controller_type):
            registry.unregister_controller(controller_type, controller["name"])
        assert len(registry.list_controllers(controller_type)) == 0


def test_registry__list_controllers(registry_fixture):
    registry = Registry(registry_filename=TEST_FILENAME)
    registry.reset_defaults()
    actual = registry.list_controllers(CTYPE)
    expected = DEFAULT_REGISTRY["Controllers"][CTYPE]
    assert len(actual) == len(expected)


def test_registry__register_controllers(registry_fixture):
    registry = Registry(registry_filename=TEST_FILENAME)
    clear_controllers(registry)
    controller = DEFAULT_REGISTRY["Controllers"][CTYPE][0]
    registry.register_controller(CTYPE, controller)
    controllers = registry.list_controllers(CTYPE)
    assert len(controllers) == 1

    # Test that the the changes are reflected with a new instance.
    registry2 = Registry(registry_filename=TEST_FILENAME)
    controllers1 = registry.list_controllers(CTYPE)
    controllers2 = registry2.list_controllers(CTYPE)
    for data1, data2 in zip(controllers1, controllers2):
        for field in DEFAULT_REGISTRY["Controllers"][CTYPE][0]:
            assert data1[field] == data2[field]


def test_registry__unregister_controllers(registry_fixture):
    registry = Registry(registry_filename=TEST_FILENAME)
    registry.reset_defaults()
    assert len(registry.list_controllers(CTYPE)) == len(DEFAULT_REGISTRY["Controllers"][CTYPE])
    clear_controllers(registry)


def test_registry__is_controller_registered(registry_fixture):
    registry = Registry(registry_filename=TEST_FILENAME)
    registry.reset_defaults()
    assert registry.is_controller_registered(CTYPE, DEFAULT_REGISTRY["Controllers"][CTYPE][0]["name"])


def test_registry__reset_defaults(registry_fixture):
    registry = Registry(registry_filename=TEST_FILENAME)
    clear_controllers(registry)
    registry.reset_defaults()
    assert len(registry.list_controllers(CTYPE)) == len(DEFAULT_REGISTRY["Controllers"][CTYPE])


def test_registry__show_controllers(capsys, registry_fixture):
    """Test functionality of show_controllers."""
    registry = Registry(registry_filename=TEST_FILENAME)
    registry.reset_defaults()
    registry.show_controllers()
    captured = capsys.readouterr()
    for controller in DEFAULT_REGISTRY["Controllers"][CTYPE]:
        assert controller["name"] in captured.out

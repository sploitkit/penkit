"""Test plugin manager functionality."""

from unittest.mock import patch, MagicMock

import pytest
from pathlib import Path

from penkit.core.plugin import PenKitPlugin, PluginManager


class SamplePlugin(PenKitPlugin):
    """Test plugin class."""

    name = "test_plugin"
    description = "Test plugin for unit tests"
    version = "0.0.1"
    author = "Test Author"

    def __init__(self) -> None:
        """Initialize the test plugin."""
        super().__init__()
        self.options = {
            "option1": "default1",
            "option2": "default2",
        }

    def run(self) -> str:
        """Run the plugin.

        Returns:
            Test string
        """
        return "Test plugin run successful"


def test_plugin_registration() -> None:
    """Test plugin registration."""
    # Create a plugin manager
    manager = PluginManager()

    # Register a plugin
    manager.register_plugin(SamplePlugin)

    # Verify the plugin was registered
    assert "test_plugin" in manager.plugins
    assert manager.plugins["test_plugin"].name == "test_plugin"
    assert manager.plugins["test_plugin"].description == "Test plugin for unit tests"


def test_plugin_get_and_set_option() -> None:
    """Test getting and setting plugin options."""
    # Create a plugin
    plugin = SamplePlugin()

    # Verify default options
    assert plugin.get_options() == {
        "option1": "default1",
        "option2": "default2",
    }

    # Set an option
    success = plugin.set_option("option1", "new_value")
    assert success is True

    # Verify the option was set
    assert plugin.get_options()["option1"] == "new_value"

    # Try to set a non-existent option
    success = plugin.set_option("invalid_option", "value")
    assert success is False


def test_plugin_manager_get_plugin() -> None:
    """Test getting a plugin by name."""
    # Create a plugin manager
    manager = PluginManager()

    # Register a plugin
    manager.register_plugin(SamplePlugin)

    # Get the plugin by name
    plugin = manager.get_plugin("test_plugin")
    assert plugin is not None
    assert plugin.name == "test_plugin"

    # Try to get a non-existent plugin
    plugin = manager.get_plugin("non_existent_plugin")
    assert plugin is None


def test_plugin_manager_get_all_plugins() -> None:
    """Test getting all plugins."""
    # Create a plugin manager
    manager = PluginManager()

    # Register a plugin
    manager.register_plugin(SamplePlugin)

    # Get all plugins
    plugins = manager.get_all_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "test_plugin"


def test_plugin_manager_unload_plugin() -> None:
    """Test unloading a plugin."""
    # Create a plugin manager
    manager = PluginManager()

    # Register a plugin
    manager.register_plugin(SamplePlugin)

    # Unload the plugin
    success = manager.unload_plugin("test_plugin")
    assert success is True

    # Verify the plugin was unloaded
    plugin = manager.get_plugin("test_plugin")
    assert plugin is None

    # Try to unload a non-existent plugin
    success = manager.unload_plugin("non_existent_plugin")
    assert success is False


@patch("importlib.import_module")
@patch("penkit.core.plugin.Path")
def test_plugin_discovery(mock_path, mock_import_module) -> None:
    """Test plugin discovery."""
    # Mock the module that would be discovered
    mock_module = type("MockModule", (), {})
    mock_module.SamplePlugin = SamplePlugin
    mock_import_module.return_value = mock_module

    # Setup mock path behavior
    mock_modules_dir = MagicMock()
    mock_path.return_value.parent.parent.__truediv__.return_value = mock_modules_dir
    mock_modules_dir.exists.return_value = True
    
    # Create a mock item to simulate a module directory
    mock_path_item = MagicMock()
    mock_path_item.name = "test_module"
    mock_path_item.is_dir.return_value = True
    
    # Setup the __truediv__ method to handle path / "__init__.py"
    mock_init_py = MagicMock()
    mock_init_py.exists.return_value = True
    mock_path_item.__truediv__.return_value = mock_init_py
    
    # Set up the iterdir to return our mock path item
    mock_modules_dir.iterdir.return_value = [mock_path_item]

    # Create a plugin manager
    manager = PluginManager()
    
    # Discover plugins
    manager._discover_internal_plugins()

    # Verify the plugin was discovered
    assert "test_plugin" in manager.plugins
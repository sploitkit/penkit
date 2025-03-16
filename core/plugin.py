"""Plugin management system for PenKit."""

import importlib
import inspect
import os
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pluggy

# Define the hook specification namespace
hookspec = pluggy.HookspecMarker("penkit")
hookimpl = pluggy.HookimplMarker("penkit")


class PenKitPlugin:
    """Base class for all PenKit plugins."""

    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"
    author: str = "PenKit Team"
    
    def __init__(self) -> None:
        """Initialize the plugin."""
        self.options: Dict[str, Any] = {}
    
    def setup(self) -> None:
        """Set up the plugin. Called when the plugin is loaded."""
        pass
    
    def cleanup(self) -> None:
        """Clean up the plugin. Called when the plugin is unloaded."""
        pass
    
    def get_options(self) -> Dict[str, Any]:
        """Get the plugin options.
        
        Returns:
            Dictionary of options
        """
        return self.options
    
    def set_option(self, option: str, value: Any) -> bool:
        """Set a plugin option.
        
        Args:
            option: Option name
            value: Option value
            
        Returns:
            True if successful, False otherwise
        """
        if option in self.options:
            self.options[option] = value
            return True
        return False
    
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the plugin.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Plugin result
        """
        raise NotImplementedError("Plugin does not implement run method")


class HookSpecs:
    """Hook specifications for PenKit plugins."""
    
    @hookspec
    def register_plugin(self) -> List[Type[PenKitPlugin]]:
        """Register plugin classes.
        
        Returns:
            List of plugin classes
        """
        pass
    
    @hookspec
    def plugin_loaded(self, plugin: PenKitPlugin) -> None:
        """Called when a plugin is loaded.
        
        Args:
            plugin: The loaded plugin instance
        """
        pass


class PluginManager:
    """Manager for PenKit plugins."""
    
    def __init__(self) -> None:
        """Initialize the plugin manager."""
        self.manager = pluggy.PluginManager("penkit")
        self.hooks = HookSpecs()
        self.manager.add_hookspecs(self.hooks)
        
        # Dictionary to store loaded plugins by name
        self.plugins: Dict[str, PenKitPlugin] = {}
    
    def register_plugin(self, plugin_class: Type[PenKitPlugin]) -> None:
        """Register and initialize a plugin.
        
        Args:
            plugin_class: The plugin class to register
        """
        plugin = plugin_class()
        self.plugins[plugin.name] = plugin
        plugin.setup()
    
    def discover_plugins(self) -> None:
        """Discover and load plugins from various sources."""
        # 1. Look for built-in plugins in the modules directory
        self._discover_internal_plugins()
        
        # 2. Look for installed plugins via entry points
        self._discover_entry_point_plugins()
        
        # 3. Look for plugins in user plugins directory
        self._discover_user_plugins()
    
    def _discover_internal_plugins(self) -> None:
        """Discover internal plugins from the modules directory."""
        modules_dir = Path(__file__).parent.parent / "modules"
        if not modules_dir.exists():
            return
        
        # Add the modules directory to sys.path temporarily
        sys.path.insert(0, str(modules_dir.parent.parent))
        
        try:
            for item in modules_dir.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    module_name = f"penkit.modules.{item.name}"
                    try:
                        module = importlib.import_module(module_name)
                        self._register_plugins_from_module(module)
                    except ImportError as e:
                        print(f"Failed to import module {module_name}: {e}")
        finally:
            # Remove the added path
            if sys.path[0] == str(modules_dir.parent.parent):
                sys.path.pop(0)
    
    def _discover_entry_point_plugins(self) -> None:
        """Discover plugins registered via entry points."""
        try:
            discovered_plugins = entry_points(group="penkit.plugins")
            for entry_point in discovered_plugins:
                try:
                    plugin_class = entry_point.load()
                    if issubclass(plugin_class, PenKitPlugin):
                        self.register_plugin(plugin_class)
                except Exception as e:
                    print(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            print(f"Failed to discover entry point plugins: {e}")
    
    def _discover_user_plugins(self) -> None:
        """Discover plugins from user plugins directory."""
        user_plugin_dir = Path.home() / ".penkit" / "plugins"
        if not user_plugin_dir.exists():
            return
        
        # Add the user plugin directory to sys.path temporarily
        sys.path.insert(0, str(user_plugin_dir))
        
        try:
            for item in user_plugin_dir.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    try:
                        module = importlib.import_module(item.name)
                        self._register_plugins_from_module(module)
                    except ImportError as e:
                        print(f"Failed to import user plugin {item.name}: {e}")
        finally:
            # Remove the added path
            if sys.path[0] == str(user_plugin_dir):
                sys.path.pop(0)
    
    def _register_plugins_from_module(self, module: Any) -> None:
        """Register plugins from a module.
        
        Args:
            module: The module to scan for plugins
        """
        for item_name in dir(module):
            item = getattr(module, item_name)
            if (
                inspect.isclass(item)
                and issubclass(item, PenKitPlugin)
                and item is not PenKitPlugin
            ):
                self.register_plugin(item)
    
    def get_plugin(self, name: str) -> Optional[PenKitPlugin]:
        """Get a plugin by name.
        
        Args:
            name: The plugin name
            
        Returns:
            The plugin instance if found, None otherwise
        """
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> List[PenKitPlugin]:
        """Get all loaded plugins.
        
        Returns:
            List of all plugin instances
        """
        return list(self.plugins.values())
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name.
        
        Args:
            name: The plugin name
            
        Returns:
            True if successful, False otherwise
        """
        if name in self.plugins:
            plugin = self.plugins[name]
            plugin.cleanup()
            del self.plugins[name]
            return True
        return False

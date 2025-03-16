"""Configuration management for PenKit."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from penkit.core.exceptions import ConfigError


class Config:
    """Configuration manager for PenKit."""

    DEFAULT_CONFIG = {
        "debug": False,
        "workdir": str(Path.cwd()),
        "tools": {
            "nmap": {
                "path": None,  # Auto-detect
                "use_container": False,
                "container_image": "instrumentisto/nmap:latest",
            },
            "sqlmap": {
                "path": None,
                "use_container": False,
                "container_image": "vulnerables/sqlmap-python3",
            },
            # Add other tools here
        },
        "sessions": {
            "path": str(Path.home() / ".penkit" / "sessions"),
        },
        "plugins": {
            "path": str(Path.home() / ".penkit" / "plugins"),
        },
    }

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._config_file = Path.home() / ".penkit" / "config.json"

        # Load config from file if it exists
        if self._config_file.exists():
            self.load_from_file(self._config_file)

        # Load config from environment variables
        self.load_from_env()

    def load_from_file(self, config_file: Path) -> None:
        """Load configuration from a file.

        Args:
            config_file: Path to the configuration file

        Raises:
            ConfigError: If loading the configuration fails
        """
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                self.update(file_config)
        except Exception as e:
            raise ConfigError(f"Failed to load configuration from {config_file}: {e}")

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Look for environment variables with prefix PENKIT_
        for key, value in os.environ.items():
            if key.startswith("PENKIT_"):
                # Convert PENKIT_DEBUG=true to config["debug"] = True
                config_key = key[7:].lower()  # Remove PENKIT_ prefix

                # Handle nested keys (e.g., PENKIT_TOOLS_NMAP_PATH)
                if "_" in config_key:
                    parts = config_key.split("_")
                    self._set_nested_config(parts, value)
                else:
                    # Convert string values to appropriate types
                    self._config[config_key] = self._parse_value(value)

    def _set_nested_config(self, key_parts: list, value: str) -> None:
        """Set a nested configuration value.

        Args:
            key_parts: Parts of the configuration key
            value: Value to set
        """
        current = self._config
        for part in key_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[key_parts[-1]] = self._parse_value(value)

    def _parse_value(self, value: str) -> Any:
        """Parse a string value to the appropriate type.

        Args:
            value: String value

        Returns:
            Parsed value (bool, int, float, or string)
        """
        # Check for boolean values
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Check for numeric values
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            # Return as string if not a number
            return value

    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration with values from a dictionary.

        Args:
            config_dict: Dictionary with configuration values
        """
        # Recursively update nested dictionaries
        self._update_nested(self._config, config_dict)

    def _update_nested(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update nested dictionaries.

        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._update_nested(target[key], value)
            else:
                target[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key (can be nested with dots, e.g., "tools.nmap.path")
            default: Default value if the key is not found

        Returns:
            Configuration value or default
        """
        if "." in key:
            # Handle nested keys
            parts = key.split(".")
            value = self._config
            for part in parts:
                if part not in value:
                    return default
                value = value[part]
            return value

        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key (can be nested with dots, e.g., "tools.nmap.path")
            value: Value to set
        """
        if "." in key:
            # Handle nested keys
            parts = key.split(".")
            target = self._config
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value
        else:
            self._config[key] = value

    def save(self, config_file: Optional[Path] = None) -> None:
        """Save configuration to a file.

        Args:
            config_file: Path to the configuration file (default: ~/.penkit/config.json)

        Raises:
            ConfigError: If saving the configuration fails
        """
        if not config_file:
            config_file = self._config_file

        # Create directory if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_file, "w") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            raise ConfigError(f"Failed to save configuration to {config_file}: {e}")

    @property
    def config(self) -> Dict[str, Any]:
        """Get the entire configuration.

        Returns:
            Configuration dictionary
        """
        return self._config


# Global configuration instance
config = Config()

"""Custom exceptions for PenKit."""


class PenKitException(Exception):
    """Base exception for all PenKit exceptions."""

    pass


class PluginError(PenKitException):
    """Exception raised for errors in the plugin system."""

    pass


class ConfigError(PenKitException):
    """Exception raised for configuration errors."""

    pass


class IntegrationError(PenKitException):
    """Exception raised for errors in tool integrations."""

    pass


class ToolExecutionError(IntegrationError):
    """Exception raised when a tool execution fails."""

    pass


class OutputParsingError(IntegrationError):
    """Exception raised when parsing tool output fails."""

    pass


class SessionError(PenKitException):
    """Exception raised for errors in session management."""

    pass


class ModuleError(PenKitException):
    """Exception raised for errors in modules."""

    pass

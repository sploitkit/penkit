"""Base classes for tool integrations."""

import asyncio
import logging
import os
import shlex
import subprocess
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from penkit.core.models import ToolResult


logger = logging.getLogger(__name__)


class ToolIntegration(ABC):
    """Base class for tool integrations."""

    name: str = "base_tool"
    description: str = "Base tool integration"
    binary_name: str = ""
    version_args: List[str] = ["--version"]
    default_args: List[str] = []
    container_image: Optional[str] = None
    container_options: List[str] = []
    
    def __init__(self) -> None:
        """Initialize the tool integration."""
        self.use_container = False
        self.binary_path: Optional[str] = None
        self.version: Optional[str] = None
        self._find_binary()
    
    def _find_binary(self) -> None:
        """Find the tool binary in the system path."""
        if not self.binary_name:
            logger.warning(f"No binary name defined for {self.name}")
            return
        
        # Check if binary exists in path
        for path in os.environ["PATH"].split(os.pathsep):
            binary_path = os.path.join(path, self.binary_name)
            if os.path.isfile(binary_path) and os.access(binary_path, os.X_OK):
                self.binary_path = binary_path
                try:
                    self.version = self._get_version()
                except Exception as e:
                    logger.warning(f"Failed to get version for {self.name}: {e}")
                return
        
        logger.warning(f"Binary {self.binary_name} not found in PATH")
        self.use_container = True
    
    def _get_version(self) -> str:
        """Get the tool version.
        
        Returns:
            Version string
            
        Raises:
            subprocess.SubprocessError: If the version command fails
        """
        if not self.binary_path:
            raise ValueError(f"Binary for {self.name} not found")
        
        result = subprocess.run(
            [self.binary_path] + self.version_args,
            capture_output=True,
            text=True,
            check=True,
        )
        
        return result.stdout.strip()
    
    def build_command(self, *args: str, **kwargs: Any) -> List[str]:
        """Build a command for the tool.
        
        Args:
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Command as a list of strings
            
        Raises:
            ValueError: If the binary is not found and container is not available
        """
        if self.binary_path:
            return [self.binary_path] + self.default_args + list(args)
        
        if self.use_container and self.container_image:
            return (
                ["docker", "run", "--rm"]
                + self.container_options
                + [self.container_image]
                + self.default_args
                + list(args)
            )
        
        raise ValueError(f"Cannot build command for {self.name}: binary not found")
    
    async def run_async(self, *args: str, **kwargs: Any) -> ToolResult:
        """Run the tool asynchronously.
        
        Args:
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            ToolResult containing the execution result
            
        Raises:
            ValueError: If the command cannot be built
        """
        cmd = self.build_command(*args)
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        
        start_time = datetime.utcnow()
        
        logger.info(f"Running command: {cmd_str}")
        
        try:
            # Create a subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Wait for the subprocess to finish
            stdout, stderr = await process.communicate()
            
            end_time = datetime.utcnow()
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            
            status = "success" if process.returncode == 0 else "error"
            
            # Parse the result
            parsed_result = None
            try:
                parsed_result = self.parse_output(stdout_str, stderr_str)
            except Exception as e:
                logger.error(f"Failed to parse output: {e}")
                status = "parse_error"
            
            return ToolResult(
                tool_name=self.name,
                command=cmd_str,
                status=status,
                start_time=start_time,
                end_time=end_time,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                parsed_result=parsed_result,
            )
        
        except Exception as e:
            end_time = datetime.utcnow()
            logger.error(f"Failed to run command: {e}")
            
            return ToolResult(
                tool_name=self.name,
                command=cmd_str,
                status="error",
                start_time=start_time,
                end_time=end_time,
                exit_code=None,
                stdout=None,
                stderr=str(e),
                parsed_result=None,
            )
    
    def run(self, *args: str, **kwargs: Any) -> ToolResult:
        """Run the tool synchronously.
        
        Args:
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            ToolResult containing the execution result
        """
        return asyncio.run(self.run_async(*args, **kwargs))
    
    @abstractmethod
    def parse_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse the tool output.
        
        Args:
            stdout: Standard output from the tool
            stderr: Standard error from the tool
            
        Returns:
            Parsed output as a dictionary
        """
        raise NotImplementedError("Tool integration must implement parse_output")


class DockerToolIntegration(ToolIntegration):
    """Base class for Docker-based tool integrations."""

    def __init__(self) -> None:
        """Initialize the Docker tool integration."""
        super().__init__()
        self.use_container = True
        
        # Check if Docker is available
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.docker_version = result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Docker not found or not available")
            self.docker_version = None
            self.use_container = False
    
    def _get_version(self) -> str:
        """Get the tool version from the Docker container.
        
        Returns:
            Version string
            
        Raises:
            subprocess.SubprocessError: If the Docker command fails
        """
        if not self.container_image:
            raise ValueError(f"No container image defined for {self.name}")
        
        result = subprocess.run(
            ["docker", "run", "--rm", self.container_image] + self.version_args,
            capture_output=True,
            text=True,
            check=True,
        )
        
        return result.stdout.strip()


class CommandBuilder:
    """Helper class for building complex command lines."""

    def __init__(self, base_command: Union[str, List[str]]) -> None:
        """Initialize the command builder.
        
        Args:
            base_command: Base command as a string or list of strings
        """
        if isinstance(base_command, str):
            self.command = [base_command]
        else:
            self.command = base_command.copy()
        
        self.args: List[str] = []
    
    def add_arg(self, arg: str) -> "CommandBuilder":
        """Add a simple argument.
        
        Args:
            arg: Argument to add
            
        Returns:
            Self for chaining
        """
        self.args.append(arg)
        return self
    
    def add_flag(self, flag: str, value: Optional[Union[str, int, bool]] = None) -> "CommandBuilder":
        """Add a flag with optional value.
        
        Args:
            flag: Flag name (e.g., "--output")
            value: Flag value (if None, the flag is added without a value)
            
        Returns:
            Self for chaining
        """
        if value is None:
            self.args.append(flag)
        elif isinstance(value, bool):
            if value:
                self.args.append(flag)
        else:
            self.args.append(flag)
            self.args.append(str(value))
        
        return self
    
    def add_key_value(self, key: str, value: Union[str, int], separator: str = "=") -> "CommandBuilder":
        """Add a key-value pair.
        
        Args:
            key: Key name
            value: Value
            separator: Separator between key and value
            
        Returns:
            Self for chaining
        """
        self.args.append(f"{key}{separator}{value}")
        return self
    
    def build(self) -> List[str]:
        """Build the final command.
        
        Returns:
            Command as a list of strings
        """
        return self.command + self.args
    
    def __str__(self) -> str:
        """Get the command as a string.
        
        Returns:
            Command as a string
        """
        return " ".join(shlex.quote(arg) for arg in self.build())


class OutputParser(ABC):
    """Base class for output parsers."""

    @abstractmethod
    def parse(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse tool output.
        
        Args:
            stdout: Standard output from the tool
            stderr: Standard error from the tool
            
        Returns:
            Parsed output as a dictionary
        """
        raise NotImplementedError("Output parser must implement parse")


class OutputHelper:
    """Helper class for handling tool output."""

    @staticmethod
    def save_to_file(content: str, prefix: str = "output", suffix: str = ".txt") -> Tuple[str, str]:
        """Save content to a temporary file.
        
        Args:
            content: Content to save
            prefix: File prefix
            suffix: File suffix
            
        Returns:
            Tuple of (file name, file path)
        """
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        with os.fdopen(fd, "w") as f:
            f.write(content)
        
        return os.path.basename(path), path
    
    @staticmethod
    def read_file(path: str) -> str:
        """Read content from a file.
        
        Args:
            path: File path
            
        Returns:
            File content
            
        Raises:
            FileNotFoundError: If the file does not exist
        """
        with open(path, "r") as f:
            return f.read()

"""Interactive shell for PenKit."""

import os
import shlex
import traceback
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.traceback import Traceback
from rich.panel import Panel
from rich.table import Table

from penkit.core.config import config
from penkit.core.exceptions import PenKitException, ToolExecutionError, OutputParsingError
from penkit.core.plugin import PluginManager
from penkit.core.session import Session


class PenKitCompleter(Completer):
    """Completer for PenKit shell commands."""

    def __init__(self, shell: "PenKitShell") -> None:
        """Initialize the completer.

        Args:
            shell: The PenKit shell instance
        """
        self.shell = shell
        self.commands = {
            "help": "Show help",
            "exit": "Exit the shell",
            "use": "Use a module",
            "show": "Show available modules/options",
            "set": "Set an option value",
            "run": "Run the current module",
            "back": "Go back to the main context",
            "sessions": "Manage sessions",
            "workspaces": "Manage workspaces",
            "config": "Manage configuration",
        }

    def get_completions(self, document: Any, complete_event: Any) -> Any:
        """Get command completions.

        Args:
            document: The document to complete
            complete_event: The complete event

        Yields:
            Completion suggestions
        """
        word = document.get_word_before_cursor()
        text = document.text_before_cursor.lstrip()

        # Complete commands
        if not text or " " not in text:
            for command in self.commands:
                if command.startswith(word):
                    yield Completion(
                        command,
                        start_position=-len(word),
                        display=command,
                        display_meta=self.commands[command],
                    )

        # Complete arguments based on command
        else:
            command = text.split()[0]

            # Complete module names for 'use' command
            if command == "use":
                for module in self.shell.plugin_manager.get_all_plugins():
                    module_name = module.name
                    if module_name.startswith(word):
                        yield Completion(
                            module_name,
                            start_position=-len(word),
                            display=module_name,
                            display_meta=module.description,
                        )

            # Complete option names for 'set' command
            elif command == "set" and self.shell.current_module:
                options = self.shell.current_module.get_options()
                arg_parts = text.split()
                if len(arg_parts) == 2:  # 'set ' or 'set part_of_option_name'
                    option_prefix = arg_parts[1] if len(arg_parts) > 1 else ""
                    for option_name in options:
                        if option_name.startswith(option_prefix):
                            yield Completion(
                                option_name,
                                start_position=-len(option_prefix),
                                display=option_name,
                                display_meta=str(options[option_name]),
                            )

            # Complete 'show' command arguments
            elif command == "show":
                show_args = ["modules", "options"]
                arg_prefix = text.split()[1] if len(text.split()) > 1 else ""

                for arg in show_args:
                    if arg.startswith(arg_prefix):
                        yield Completion(
                            arg,
                            start_position=-len(arg_prefix),
                            display=arg,
                            display_meta=f"Show {arg}",
                        )


class PenKitShell:
    """Interactive shell for PenKit."""

    def __init__(
        self, plugin_manager: PluginManager, workdir: str = os.getcwd()
    ) -> None:
        """Initialize the PenKit shell.

        Args:
            plugin_manager: The plugin manager instance
            workdir: Working directory for the shell
        """
        self.plugin_manager = plugin_manager
        self.workdir = Path(workdir)
        self.current_module: Optional[Any] = None
        self.console = Console()
        self.debug_mode = config.get("debug", False)

        # Create history file directory if it doesn't exist
        history_dir = Path.home() / ".penkit"
        history_dir.mkdir(exist_ok=True)

        # Initialize session with prompt_toolkit
        self.session = PromptSession(
            history=FileHistory(str(history_dir / "history")),
            auto_suggest=AutoSuggestFromHistory(),
            completer=PenKitCompleter(self),
            style=Style.from_dict({"prompt": "ansigreen bold"}),
        )

        # Create a session
        self.penkit_session = Session(name="default", path=self.workdir)

    def _get_prompt(self) -> str:
        """Get the current prompt string.

        Returns:
            The formatted prompt string
        """
        if self.current_module:
            return f"penkit ({self.current_module.name}) > "
        return "penkit > "

    def _process_command(self, command: str, args: List[str]) -> bool:
        """Process a shell command.

        Args:
            command: The command to process
            args: List of command arguments

        Returns:
            True if the shell should continue, False if it should exit
        """
        try:
            if command == "exit" or command == "quit":
                return False

            elif command == "help":
                self._show_help()

            elif command == "use":
                if not args:
                    self.console.print("[bold red]Error: Missing module name[/bold red]")
                    return True

                module_name = args[0]
                plugin = self.plugin_manager.get_plugin(module_name)

                if plugin:
                    self.current_module = plugin
                    self.console.print(
                        f"[bold green]Using module: {module_name}[/bold green]"
                    )
                else:
                    self.console.print(
                        f"[bold red]Module not found: {module_name}[/bold red]"
                    )
                    # Show available modules as a helpful suggestion
                    self.console.print("[yellow]Available modules:[/yellow]")
                    for available_plugin in self.plugin_manager.get_all_plugins():
                        self.console.print(f"  {available_plugin.name}")

            elif command == "show":
                if not args:
                    self.console.print("[yellow]Usage: show [modules|options][/yellow]")
                    return True
                
                if args[0] == "modules":
                    self._show_modules()
                elif args[0] == "options" and self.current_module:
                    self._show_options()
                elif args[0] == "options" and not self.current_module:
                    self.console.print("[bold yellow]No module selected. Use 'use <module>' first.[/bold yellow]")
                else:
                    self.console.print(f"[bold red]Invalid argument for 'show': {args[0]}[/bold red]")
                    self.console.print("[yellow]Valid options are: modules, options[/yellow]")

            elif command == "set":
                if not self.current_module:
                    self.console.print("[bold red]No module selected[/bold red]")
                    self.console.print("[yellow]Use 'use <module>' to select a module first[/yellow]")
                elif len(args) < 2:
                    self.console.print("[bold red]Usage: set <option> <value>[/bold red]")
                    if self.current_module:
                        self.console.print("[yellow]Available options:[/yellow]")
                        self._show_options()
                else:
                    option = args[0]
                    value = " ".join(args[1:])

                    # Convert value to appropriate type based on current option value
                    current_value = self.current_module.options.get(option)
                    if current_value is not None:
                        try:
                            if isinstance(current_value, bool):
                                # Handle boolean values
                                if value.lower() in ("true", "yes", "1", "on"):
                                    value = True
                                elif value.lower() in ("false", "no", "0", "off"):
                                    value = False
                                else:
                                    self.console.print(
                                        f"[bold yellow]Warning: Converting '{value}' to boolean[/bold yellow]"
                                    )
                                    value = bool(value)
                            elif isinstance(current_value, int):
                                value = int(value)
                            elif isinstance(current_value, float):
                                value = float(value)
                        except (ValueError, TypeError) as e:
                            self.console.print(
                                f"[bold red]Error: Could not convert '{value}' to {type(current_value).__name__}[/bold red]"
                            )
                            self.console.print(
                                f"[yellow]Details: {str(e)}[/yellow]"
                            )
                            return True

                    # Set the option value
                    if self.current_module.set_option(option, value):
                        self.console.print(f"[green]Set {option} -> {value}[/green]")
                    else:
                        self.console.print(f"[bold red]Unknown option: {option}[/bold red]")
                        self.console.print("[yellow]Available options:[/yellow]")
                        self._show_options()

            elif command == "run":
                if not self.current_module:
                    self.console.print("[bold red]No module selected[/bold red]")
                    self.console.print("[yellow]Use 'use <module>' to select a module first[/yellow]")
                else:
                    try:
                        self.console.print(
                            f"[bold]Running module: {self.current_module.name}[/bold]"
                        )
                        result = self.current_module.run()
                        self.console.print(
                            "[bold green]Module execution completed[/bold green]"
                        )

                        # Save result to current session
                        try:
                            self.penkit_session.save_scan_result(
                                self.current_module.name, result
                            )
                        except Exception as save_error:
                            self.console.print(
                                f"[bold yellow]Warning: Could not save results: {str(save_error)}[/bold yellow]"
                            )
                            if self.debug_mode:
                                self.console.print_exception()

                        # Display result summary based on type
                        if isinstance(result, dict):
                            if "hosts" in result:
                                host_count = len(result['hosts'])
                                self.console.print(
                                    f"[green]Found {host_count} host{'s' if host_count != 1 else ''}[/green]"
                                )
                                
                                # Create a table for better visualization
                                table = Table(title="Discovered Hosts")
                                table.add_column("IP Address", style="cyan")
                                table.add_column("Hostname", style="green")
                                table.add_column("Open Ports", style="yellow")
                                
                                for host in result["hosts"]:
                                    ip = host.get("ip_address", "Unknown")
                                    hostname = host.get("hostname", "")
                                    
                                    open_ports = host.get("open_ports", [])
                                    port_str = str(len(open_ports)) if open_ports else "0"
                                    
                                    table.add_row(ip, hostname or "N/A", port_str)
                                
                                self.console.print(table)
                                
                                # Add detailed port display
                                for host in result["hosts"]:
                                    open_ports = host.get("open_ports", [])
                                    if open_ports:
                                        ip = host.get("ip_address", "Unknown")
                                        port_table = Table(title=f"Open Ports on {ip}")
                                        port_table.add_column("Port", style="cyan")
                                        port_table.add_column("Protocol", style="green")
                                        port_table.add_column("State", style="yellow")
                                        port_table.add_column("Service", style="magenta")
                                        port_table.add_column("Version", style="blue")
                                        
                                        for port in open_ports:
                                            if port.get("state") == "open":
                                                port_table.add_row(
                                                    str(port.get("port", "")),
                                                    port.get("protocol", ""),
                                                    port.get("state", ""),
                                                    port.get("service", "") or "unknown",
                                                    port.get("version", "") or ""
                                                )
                                        
                                        self.console.print(port_table)
                                        
                                        # Add banner information if available
                                        for port in open_ports:
                                            if port.get("banner"):
                                                banner_panel = Panel(
                                                    port.get("banner", ""),
                                                    title=f"Banner for Port {port.get('port')}",
                                                    border_style="blue"
                                                )
                                                self.console.print(banner_panel)
                                
                            elif "vulnerabilities" in result:
                                vuln_count = len(result['vulnerabilities'])
                                self.console.print(
                                    f"[green]Found {vuln_count} vulnerabilit{'ies' if vuln_count != 1 else 'y'}[/green]"
                                )
                                
                                # Create a table for better visualization
                                table = Table(title="Discovered Vulnerabilities")
                                table.add_column("Type", style="cyan")
                                table.add_column("URL", style="green")
                                table.add_column("Severity", style="yellow")
                                
                                for vuln in result["vulnerabilities"]:
                                    vuln_type = vuln.get("type", "Unknown")
                                    url = vuln.get("url", "N/A")
                                    severity = vuln.get("severity", "Unknown")
                                    
                                    table.add_row(vuln_type, url, severity)
                                
                                self.console.print(table)
                            else:
                                # Generic result display for other types of results
                                self.console.print(f"[yellow]Result:[/yellow]")
                                try:
                                    self.console.print(json.dumps(result, indent=2))
                                except Exception:
                                    self.console.print(str(result))
                        else:
                            self.console.print(f"Result: {result}")
                    except ToolExecutionError as e:
                        self.console.print_exception() if self.debug_mode else None
                        self.console.print(
                            Panel(
                                f"[bold red]Tool Execution Error:[/bold red]\n{str(e)}",
                                title="Error",
                                border_style="red"
                            )
                        )
                        # Suggest potential fixes
                        self.console.print(
                            "[yellow]Possible solutions:[/yellow]\n"
                            "1. Check if the target is reachable\n"
                            "2. Verify that required tools are installed\n"
                            "3. Try running with --debug flag for more details\n"
                            "4. If using a container, check Docker status"
                        )
                    except OutputParsingError as e:
                        self.console.print_exception() if self.debug_mode else None
                        self.console.print(
                            Panel(
                                f"[bold red]Output Parsing Error:[/bold red]\n{str(e)}",
                                title="Error",
                                border_style="red"
                            )
                        )
                        # Show raw output if available
                        if hasattr(e, 'stdout') and e.stdout:
                            self.console.print("[yellow]Raw output (first 200 chars):[/yellow]")
                            self.console.print(e.stdout[:200] + "..." if len(e.stdout) > 200 else e.stdout)
                    except PenKitException as e:
                        self.console.print_exception() if self.debug_mode else None
                        self.console.print(
                            Panel(
                                f"[bold red]Error:[/bold red]\n{str(e)}",
                                title=type(e).__name__,
                                border_style="red"
                            )
                        )
                    except Exception as e:
                        self.console.print_exception() if self.debug_mode else None
                        self.console.print(
                            Panel(
                                f"[bold red]Unexpected Error:[/bold red]\n{str(e)}",
                                title="Error",
                                border_style="red"
                            )
                        )
                        self.console.print(
                            "[yellow]This appears to be an unexpected error. Please report this issue.[/yellow]"
                        )

            elif command == "back":
                self.current_module = None
                self.console.print("[bold blue]Returned to main context[/bold blue]")

            elif command == "config":
                self._handle_config_command(args)

            else:
                self.console.print(f"[bold red]Unknown command: {command}[/bold red]")
                self.console.print("[yellow]Type 'help' for a list of available commands[/yellow]")

            return True
        except Exception as e:
            self.console.print_exception() if self.debug_mode else None
            self.console.print(
                Panel(
                    f"[bold red]Shell Error:[/bold red]\n{str(e)}",
                    title="Shell Error",
                    border_style="red"
                )
            )
            return True

    def _handle_config_command(self, args: List[str]) -> None:
        """Handle the 'config' command.

        Args:
            args: Command arguments
        """
        try:
            if not args:
                # Show all config
                table = Table(title="Current Configuration")
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="green")
                
                for key, value in config.config.items():
                    if isinstance(value, dict):
                        table.add_row(key, "...")
                        for subkey, subvalue in value.items():
                            table.add_row(f"  {key}.{subkey}", str(subvalue))
                    else:
                        table.add_row(key, str(value))
                        
                self.console.print(table)
                return

            if args[0] == "get" and len(args) > 1:
                # Get specific config value
                key = args[1]
                value = config.get(key)
                if value is None:
                    self.console.print(f"[yellow]No configuration found for key: {key}[/yellow]")
                else:
                    self.console.print(f"[cyan]{key}[/cyan] = [green]{value}[/green]")

            elif args[0] == "set" and len(args) > 2:
                # Set config value
                key = args[1]
                value = " ".join(args[2:])

                # Try to convert value to appropriate type
                try:
                    parsed_value = config._parse_value(value)
                    config.set(key, parsed_value)
                    self.console.print(f"[green]Set {key} = {parsed_value}[/green]")
                except Exception as e:
                    self.console.print(f"[bold red]Error setting config value: {str(e)}[/bold red]")

            elif args[0] == "save":
                # Save config to file
                try:
                    config.save()
                    self.console.print("[green]Configuration saved successfully[/green]")
                except Exception as e:
                    self.console.print(
                        f"[bold red]Error saving configuration: {e}[/bold red]"
                    )
                    if self.debug_mode:
                        self.console.print_exception()

            else:
                self.console.print("[bold red]Invalid config command[/bold red]")
                self.console.print(Panel(
                    "config - Show all configuration\n"
                    "config get <key> - Get configuration value\n"
                    "config set <key> <value> - Set configuration value\n"
                    "config save - Save configuration to file",
                    title="Config Command Usage",
                    border_style="blue"
                ))
        except Exception as e:
            self.console.print(f"[bold red]Error in config command: {str(e)}[/bold red]")
            if self.debug_mode:
                self.console.print_exception()

    def _show_help(self) -> None:
        """Display help information."""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="green")
        
        help_table.add_row("help", "Show this help message")
        help_table.add_row("use <module>", "Select a module to use")
        help_table.add_row("show modules", "Show available modules")
        help_table.add_row("show options", "Show module options")
        help_table.add_row("set <option> <value>", "Set a module option")
        help_table.add_row("run", "Run the current module")
        help_table.add_row("back", "Return to main context")
        help_table.add_row("config", "Manage configuration")
        help_table.add_row("exit", "Exit the shell")
        
        self.console.print(help_table)

    def _show_modules(self) -> None:
        """Display available modules."""
        modules_table = Table(title="Available Modules")
        modules_table.add_column("Name", style="cyan")
        modules_table.add_column("Description", style="green")
        modules_table.add_column("Version", style="yellow")
        
        plugins = self.plugin_manager.get_all_plugins()
        if not plugins:
            self.console.print("[yellow]No modules available[/yellow]")
            return
            
        for plugin in plugins:
            modules_table.add_row(
                plugin.name, 
                plugin.description, 
                plugin.version
            )
            
        self.console.print(modules_table)

    def _show_options(self) -> None:
        """Display options for the current module."""
        if not self.current_module:
            self.console.print("[bold yellow]No module selected[/bold yellow]")
            return

        options = self.current_module.get_options()

        if not options:
            self.console.print("  No options available")
            return

        options_table = Table(title=f"Options for module: {self.current_module.name}")
        options_table.add_column("Option", style="cyan")
        options_table.add_column("Value", style="green")
        options_table.add_column("Type", style="yellow")

        for name, value in options.items():
            # Format value based on type
            if isinstance(value, bool):
                value_str = "yes" if value else "no"
            else:
                value_str = str(value)

            # Add row to table
            options_table.add_row(
                name,
                value_str,
                type(value).__name__
            )
            
        self.console.print(options_table)

    def run_script(self, script_file: str) -> None:
        """Run a script file with commands.

        Args:
            script_file: Path to the script file
        """
        try:
            script_path = Path(script_file)
            if not script_path.exists():
                self.console.print(f"[bold red]Error: Script file not found: {script_file}[/bold red]")
                return
                
            with open(script_file, "r") as f:
                self.console.print(f"[bold blue]Running script: {script_file}[/bold blue]")
                
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    self.console.print(f"[dim]> {line}[/dim]")

                    try:
                        continue_shell = self.handle_input(line)
                        if not continue_shell:
                            self.console.print("[yellow]Script execution stopped by exit command[/yellow]")
                            break
                    except Exception as e:
                        self.console.print(
                            f"[bold red]Error at line {line_number}: {str(e)}[/bold red]"
                        )
                        if self.debug_mode:
                            self.console.print_exception()
                        
                        # Ask whether to continue execution
                        if not self.debug_mode:
                            self.console.print("[yellow]Continue script execution? (y/n)[/yellow]")
                            try:
                                choice = input().strip().lower()
                                if choice != 'y':
                                    self.console.print("[bold]Stopping script execution[/bold]")
                                    break
                            except (KeyboardInterrupt, EOFError):
                                self.console.print("[bold]Stopping script execution[/bold]")
                                break
                
                self.console.print("[bold green]Script execution completed[/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Error running script: {str(e)}[/bold red]")
            if self.debug_mode:
                self.console.print_exception()

    def handle_input(self, user_input: str) -> bool:
        """Handle user input.

        Args:
            user_input: The user input string

        Returns:
            True if the shell should continue, False if it should exit
        """
        user_input = user_input.strip()
        if not user_input:
            return True

        try:
            args = shlex.split(user_input)
            command = args[0].lower()
            return self._process_command(command, args[1:])
        except Exception as e:
            if self.debug_mode:
                self.console.print_exception()
            else:
                self.console.print(
                    Panel(
                        f"[bold red]Input Error:[/bold red]\n{str(e)}",
                        title="Input Error",
                        border_style="red"
                    )
                )
            return True

    def start(self) -> None:
        """Start the interactive shell."""
        self.console.print(
            Panel(
                "[bold]Welcome to PenKit - Advanced Penetration Testing Toolkit[/bold]\n"
                "Type 'help' for a list of commands",
                title="PenKit",
                border_style="blue"
            )
        )

        while True:
            try:
                user_input = self.session.prompt(self._get_prompt())
                continue_shell = self.handle_input(user_input)
                if not continue_shell:
                    break
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]Use 'exit' to quit[/bold yellow]")
            except EOFError:
                break
            except Exception as e:
                if self.debug_mode:
                    self.console.print_exception()
                else:
                    self.console.print(
                        Panel(
                            f"[bold red]Unexpected error:[/bold red]\n{str(e)}",
                            title="Error",
                            border_style="red"
                        )
                    )

        self.console.print(Panel("[bold]Thank you for using PenKit![/bold]", title="Goodbye", border_style="green"))
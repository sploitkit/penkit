"""Interactive shell for PenKit."""

import os
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

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
                self.console.print(f"[bold green]Using module: {module_name}[/bold green]")
            else:
                self.console.print(f"[bold red]Module not found: {module_name}[/bold red]")
        
        elif command == "show":
            if not args or args[0] == "modules":
                self._show_modules()
            elif args[0] == "options" and self.current_module:
                self._show_options()
            else:
                self.console.print("[bold red]Invalid argument for 'show'[/bold red]")
        
        elif command == "set":
            if not self.current_module:
                self.console.print("[bold red]No module selected[/bold red]")
            elif len(args) < 2:
                self.console.print("[bold red]Usage: set <option> <value>[/bold red]")
            else:
                # This would set an option in the current module
                option = args[0]
                value = " ".join(args[1:])
                self.console.print(f"Setting {option} -> {value}")
                # Actual implementation would call module.set_option(option, value)
        
        elif command == "run":
            if not self.current_module:
                self.console.print("[bold red]No module selected[/bold red]")
            else:
                self.console.print(f"[bold]Running module: {self.current_module.name}[/bold]")
                # Actual implementation would call module.run()
        
        elif command == "back":
            self.current_module = None
            self.console.print("[bold blue]Returned to main context[/bold blue]")
        
        else:
            self.console.print(f"[bold red]Unknown command: {command}[/bold red]")
        
        return True

    def _show_help(self) -> None:
        """Display help information."""
        self.console.print("[bold]Available Commands:[/bold]")
        self.console.print("  help                - Show this help message")
        self.console.print("  use <module>        - Select a module to use")
        self.console.print("  show modules        - Show available modules")
        self.console.print("  show options        - Show module options")
        self.console.print("  set <option> <value> - Set a module option")
        self.console.print("  run                 - Run the current module")
        self.console.print("  back                - Return to main context")
        self.console.print("  exit                - Exit the shell")

    def _show_modules(self) -> None:
        """Display available modules."""
        self.console.print("[bold]Available Modules:[/bold]")
        for plugin in self.plugin_manager.get_all_plugins():
            self.console.print(f"  {plugin.name} - {plugin.description}")

    def _show_options(self) -> None:
        """Display options for the current module."""
        if not self.current_module:
            return
        
        self.console.print(f"[bold]Options for module: {self.current_module.name}[/bold]")
        # This would show options for the current module
        # Actual implementation would iterate through module.get_options()
        self.console.print("  No options available yet")

    def run_script(self, script_file: str) -> None:
        """Run a script file with commands.

        Args:
            script_file: Path to the script file
        """
        with open(script_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                self.console.print(f"[dim]> {line}[/dim]")
                continue_shell = self.handle_input(line)
                if not continue_shell:
                    break

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
            self.console.print(f"[bold red]Error: {str(e)}[/bold red]")
            return True

    def start(self) -> None:
        """Start the interactive shell."""
        self.console.print("[bold blue]PenKit - Advanced Penetration Testing Toolkit[/bold blue]")
        self.console.print("Type 'help' for a list of commands\n")
        
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
        
        self.console.print("\n[bold green]Goodbye![/bold green]")
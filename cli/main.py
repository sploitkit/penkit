#!/usr/bin/env python3
"""Main CLI entry point for PenKit."""

import os
import sys
from pathlib import Path

import click
from rich.console import Console

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.shell import PenKitShell
from core.plugin import PluginManager

console = Console()


@click.group(invoke_without_command=True)
@click.option(
    "--workdir",
    "-w",
    default=os.getcwd(),
    help="Working directory for the session",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--config",
    "-c",
    default=None,
    help="Configuration file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.version_option(package_name="penkit")
@click.pass_context
def main(ctx: click.Context, workdir: str, config: str, debug: bool) -> None:
    """
    PenKit: Advanced Open-Source Penetration Testing Toolkit.

    Run without subcommands to start the interactive shell.
    """
    ctx.ensure_object(dict)
    ctx.obj["workdir"] = workdir
    ctx.obj["config"] = config
    ctx.obj["debug"] = debug

    # Setup logging based on debug flag
    if debug:
        # Set up debugging configuration here
        pass

    # If no subcommand is provided, launch the interactive shell
    if ctx.invoked_subcommand is None:
        try:
            # Initialize plugin manager
            plugin_manager = PluginManager()
            
            # Load core plugins
            plugin_manager.discover_plugins()
            
            # Create and start the shell
            shell = PenKitShell(plugin_manager, workdir=workdir)
            shell.start()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session terminated by user.[/bold yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            if debug:
                console.print_exception()
            sys.exit(1)


@main.command()
@click.argument("plugin_name", required=False)
@click.pass_context
def plugins(ctx: click.Context, plugin_name: str = None) -> None:
    """List available plugins or show details about a specific plugin."""
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()

    if plugin_name:
        # Show details for a specific plugin
        plugin = plugin_manager.get_plugin(plugin_name)
        if plugin:
            console.print(f"[bold]{plugin.name}[/bold] - {plugin.description}")
            console.print(f"Version: {plugin.version}")
            console.print(f"Author: {plugin.author}")
            # Add more details as needed
        else:
            console.print(f"[bold red]Plugin '{plugin_name}' not found.[/bold red]")
    else:
        # List all plugins
        console.print("[bold]Available Plugins:[/bold]")
        for plugin in plugin_manager.get_all_plugins():
            console.print(f"[bold]{plugin.name}[/bold] - {plugin.description}")


@main.command()
@click.argument("script_file", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.pass_context
def script(ctx: click.Context, script_file: str) -> None:
    """Run a script file with PenKit commands."""
    try:
        plugin_manager = PluginManager()
        plugin_manager.discover_plugins()
        
        shell = PenKitShell(plugin_manager, workdir=ctx.obj["workdir"])
        shell.run_script(script_file)
    except Exception as e:
        console.print(f"[bold red]Error running script: {str(e)}[/bold red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
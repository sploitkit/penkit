#!/usr/bin/env python3
"""Main CLI entry point for PenKit."""

import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console

from penkit.cli.shell import PenKitShell
from penkit.core.config import config
from penkit.core.exceptions import PenKitException
from penkit.core.plugin import PluginManager

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.penkit/penkit.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("penkit")


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
def main(ctx: click.Context, workdir: str, config_file: str, debug: bool) -> None:
    """
    PenKit: Advanced Open-Source Penetration Testing Toolkit.

    Run without subcommands to start the interactive shell.
    """
    ctx.ensure_object(dict)
    ctx.obj["workdir"] = workdir
    ctx.obj["config_file"] = config_file
    ctx.obj["debug"] = debug

    # Update configuration
    config.set("debug", debug)
    config.set("workdir", workdir)
    
    if config_file:
        try:
            config.load_from_file(Path(config_file))
        except Exception as e:
            console.print(f"[bold red]Error loading configuration: {e}[/bold red]")
            sys.exit(1)

    # Setup logging based on debug flag
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

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
        except PenKitException as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")
            if debug:
                console.print_exception()
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")
            if debug:
                console.print_exception()
            sys.exit(1)


@main.command()
@click.argument("plugin_name", required=False)
@click.pass_context
def plugins(ctx: click.Context, plugin_name: str = None) -> None:
    """List available plugins or show details about a specific plugin."""
    try:
        plugin_manager = PluginManager()
        plugin_manager.discover_plugins()

        if plugin_name:
            # Show details for a specific plugin
            plugin = plugin_manager.get_plugin(plugin_name)
            if plugin:
                console.print(f"[bold]{plugin.name}[/bold] - {plugin.description}")
                console.print(f"Version: {plugin.version}")
                console.print(f"Author: {plugin.author}")
                
                # Show plugin options
                options = plugin.get_options()
                if options:
                    console.print("\n[bold]Options:[/bold]")
                    for name, value in options.items():
                        console.print(f"  {name} = {value}")
                else:
                    console.print("\nNo options available")
            else:
                console.print(f"[bold red]Plugin '{plugin_name}' not found.[/bold red]")
        else:
            # List all plugins
            plugins_list = plugin_manager.get_all_plugins()
            
            if not plugins_list:
                console.print("[yellow]No plugins found.[/yellow]")
                return
                
            console.print(f"[bold]Available Plugins ({len(plugins_list)}):[/bold]")
            
            for plugin in plugins_list:
                console.print(f"[bold]{plugin.name}[/bold] - {plugin.description}")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


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


@main.command()
@click.option("--save", is_flag=True, help="Save configuration to file")
@click.pass_context
def config_cmd(ctx: click.Context, save: bool) -> None:
    """Manage configuration."""
    try:
        if save:
            config.save()
            console.print("[green]Configuration saved[/green]")
            return
            
        # Display current configuration
        console.print("[bold]Current Configuration:[/bold]")
        
        for key, value in config.config.items():
            if isinstance(value, dict):
                console.print(f"[bold]{key}:[/bold]")
                for subkey, subvalue in value.items():
                    console.print(f"  {subkey}: {subvalue}")
            else:
                console.print(f"{key}: {value}")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    # Ensure ~/.penkit directory exists
    os.makedirs(os.path.expanduser("~/.penkit"), exist_ok=True)
    
    main()
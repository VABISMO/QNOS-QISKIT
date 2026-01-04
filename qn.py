# qnos.py
import logging
from rich.console import Console
from rich.logging import RichHandler
import pyfiglet
import click
from lib.core import CustomHelpGroup
from lib.commands import register_commands

# Setup rich logging
FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True, show_path=True)]
)
logger = logging.getLogger(__name__)
rich_console = Console()

# Educational Banner
def print_banner():
    banner = pyfiglet.figlet_format("QNOS", font="slant")
    rich_console.print(banner, style="bold magenta")
    rich_console.print("[yellow]Notice: QNOS Qiskit Backend Platform for Solid State Spin Defect.[/yellow]")

print_banner()

# CLI
@click.group(cls=CustomHelpGroup, help_headers_color='yellow', help_options_color='green')
def cli():
    """QNOS - Number Output Signal Quantum Hardware."""
    pass

register_commands(cli)

if __name__ == "__main__":
    cli()
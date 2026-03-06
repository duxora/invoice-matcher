"""Shared Rich console and theme for CLI output."""
from rich.console import Console
from rich.theme import Theme

STATUS_COLORS = {
    "success": "green",
    "failed": "red",
    "timeout": "yellow",
    "crashed": "magenta",
    "running": "cyan",
    "never": "dim",
}

TICKET_COLORS = {
    "open": "red",
    "investigating": "yellow",
    "resolved": "green",
    "closed": "dim",
}

SEVERITY_COLORS = {
    "error": "red",
    "action": "yellow",
    "warning": "#ff8800",
    "info": "green",
}

SEVERITY_ICONS = {
    "error": "[red]X[/red]",
    "action": "[yellow]![/yellow]",
    "warning": "[#ff8800]~[/#ff8800]",
    "info": "[green].[/green]",
}

DOCTOR_OK = "[green]OK[/green]"
DOCTOR_FAIL = "[red]!![/red]"

CS_THEME = Theme({
    "status.success": "green",
    "status.failed": "red",
    "status.timeout": "yellow",
    "heading": "bold cyan",
    "label": "bold",
    "dim": "dim",
})

console = Console(theme=CS_THEME)

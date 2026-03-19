"""Windows right-click context menu installer (WSL/Windows only)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()

REG_TEMPLATE = r"""Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux]
@="Open cmux here"
"Icon"="wt.exe"

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux\command]
@="wt.exe -p \"Ubuntu\" -- wsl.exe bash -c \"cd '%V' && cmux start\""

[HKEY_CURRENT_USER\Software\Classes\Directory\shell\cmux]
@="Open cmux here"
"Icon"="wt.exe"

[HKEY_CURRENT_USER\Software\Classes\Directory\shell\cmux\command]
@="wt.exe -p \"Ubuntu\" -- wsl.exe bash -c \"cd '%V' && cmux start\""

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux_dashboard]
@="Open cmux dashboard here"
"Extended"=""
"Icon"="wt.exe"

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux_dashboard\command]
@="wt.exe -p \"Ubuntu\" -- wsl.exe bash -c \"cd '%V' && cmux dashboard\""
"""

UNREG_TEMPLATE = r"""Windows Registry Editor Version 5.00

[-HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux]
[-HKEY_CURRENT_USER\Software\Classes\Directory\shell\cmux]
[-HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\cmux_dashboard]
"""


def install_context_menu() -> None:
    """Install Windows Explorer right-click context menu entries."""
    reg_file = Path(tempfile.mktemp(suffix=".reg"))
    try:
        reg_file.write_text(REG_TEMPLATE, encoding="utf-16-le")
        result = subprocess.run(
            ["reg.exe", "import", str(reg_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Context menu installed successfully![/green]")
            console.print("Right-click any folder in Explorer → 'Open cmux here'")
            console.print("Shift+right-click → 'Open cmux dashboard here'")
        else:
            console.print(f"[red]Failed to install context menu:[/red] {result.stderr}")
    finally:
        reg_file.unlink(missing_ok=True)


def uninstall_context_menu() -> None:
    """Remove Windows Explorer right-click context menu entries."""
    reg_file = Path(tempfile.mktemp(suffix=".reg"))
    try:
        reg_file.write_text(UNREG_TEMPLATE, encoding="utf-16-le")
        result = subprocess.run(
            ["reg.exe", "import", str(reg_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Context menu removed successfully.[/green]")
        else:
            console.print(f"[red]Failed to remove context menu:[/red] {result.stderr}")
    finally:
        reg_file.unlink(missing_ok=True)

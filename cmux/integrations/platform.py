"""Platform detection and dispatcher for context menu integration."""

from __future__ import annotations

import sys


def get_platform() -> str:
    """Return 'macos', 'windows', 'wsl', or 'linux'."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    elif sys.platform.startswith("linux"):
        # Check if running under WSL
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
            if "microsoft" in version_info or "wsl" in version_info:
                return "wsl"
        except FileNotFoundError:
            pass
        return "linux"
    return "unknown"


def install_context_menu() -> None:
    """Install the right-click / context menu integration for the current platform."""
    platform = get_platform()

    if platform == "macos":
        from cmux.integrations.macos_context import install_context_menu as install
        install()
    elif platform in ("windows", "wsl"):
        from cmux.integrations.windows_context import install_context_menu as install
        install()
    elif platform == "linux":
        _install_linux_context_menu()
    else:
        from rich.console import Console
        Console().print(f"[red]Unsupported platform: {sys.platform}[/red]")


def uninstall_context_menu() -> None:
    """Remove the right-click / context menu integration for the current platform."""
    platform = get_platform()

    if platform == "macos":
        from cmux.integrations.macos_context import uninstall_context_menu as uninstall
        uninstall()
    elif platform in ("windows", "wsl"):
        from cmux.integrations.windows_context import uninstall_context_menu as uninstall
        uninstall()
    elif platform == "linux":
        _uninstall_linux_context_menu()
    else:
        from rich.console import Console
        Console().print(f"[red]Unsupported platform: {sys.platform}[/red]")


def _install_linux_context_menu() -> None:
    """Install Nautilus script for Linux desktops."""
    from pathlib import Path

    from rich.console import Console

    console = Console()

    scripts_dir = Path.home() / ".local" / "share" / "nautilus" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    script = scripts_dir / "Open cmux here"
    script.write_text(
        "#!/bin/bash\n"
        'DIR="$NAUTILUS_SCRIPT_CURRENT_URI"\n'
        'DIR="${DIR#file://}"\n'
        'gnome-terminal -- bash -c "cd \\"$DIR\\" && cmux start; exec bash"\n'
    )
    script.chmod(0o755)

    dashboard_script = scripts_dir / "Open cmux dashboard here"
    dashboard_script.write_text(
        "#!/bin/bash\n"
        'DIR="$NAUTILUS_SCRIPT_CURRENT_URI"\n'
        'DIR="${DIR#file://}"\n'
        'gnome-terminal -- bash -c "cd \\"$DIR\\" && cmux dashboard; exec bash"\n'
    )
    dashboard_script.chmod(0o755)

    console.print("[green]Nautilus scripts installed![/green]")
    console.print("Right-click in Nautilus → Scripts → 'Open cmux here'")


def _uninstall_linux_context_menu() -> None:
    """Remove Nautilus scripts."""
    from pathlib import Path

    from rich.console import Console

    console = Console()

    scripts_dir = Path.home() / ".local" / "share" / "nautilus" / "scripts"
    removed = 0
    for name in ["Open cmux here", "Open cmux dashboard here"]:
        script = scripts_dir / name
        if script.exists():
            script.unlink()
            console.print(f"[green]Removed:[/green] {script}")
            removed += 1

    if removed:
        console.print("[green]Nautilus scripts removed.[/green]")
    else:
        console.print("[dim]No cmux scripts found to remove.[/dim]")

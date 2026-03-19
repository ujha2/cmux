"""macOS Finder Quick Action (Service) installer for right-click integration."""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

SERVICES_DIR = Path.home() / "Library" / "Services"

# Automator workflow structure for "Open cmux here"
WORKFLOW_NAME_START = "Open cmux here.workflow"
WORKFLOW_NAME_DASHBOARD = "Open cmux dashboard here.workflow"


def _find_cmux_path() -> str:
    """Find the installed cmux binary path."""
    result = subprocess.run(["which", "cmux"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    # Fallback: check common locations
    for candidate in [
        Path.home() / "Library" / "Python" / "3.9" / "bin" / "cmux",
        Path.home() / "Library" / "Python" / "3.11" / "bin" / "cmux",
        Path.home() / "Library" / "Python" / "3.12" / "bin" / "cmux",
        Path("/usr/local/bin/cmux"),
        Path("/opt/homebrew/bin/cmux"),
    ]:
        if candidate.exists():
            return str(candidate)
    return "cmux"


def _find_terminal_app() -> str:
    """Find the preferred terminal application."""
    for app in ["iTerm", "Terminal"]:
        app_path = Path(f"/Applications/{app}.app")
        if app_path.exists():
            return app
    return "Terminal"


def _create_workflow(name: str, cmux_command: str) -> Path:
    """Create an Automator Quick Action workflow bundle."""
    workflow_dir = SERVICES_DIR / name
    contents_dir = workflow_dir / "Contents"

    # Clean up any existing workflow
    if workflow_dir.exists():
        shutil.rmtree(workflow_dir)

    contents_dir.mkdir(parents=True)

    cmux_path = _find_cmux_path()
    terminal = _find_terminal_app()

    # Shell script that opens terminal and runs cmux
    if terminal == "iTerm":
        script = f"""#!/bin/bash
for f in "$@"; do
    if [ -d "$f" ]; then
        DIR="$f"
    else
        DIR=$(dirname "$f")
    fi
    osascript -e 'tell application "iTerm"
        activate
        set newWindow to (create window with default profile)
        tell current session of newWindow
            write text "cd '"'"''"$DIR"''"'"' && {cmux_path} {cmux_command}"
        end tell
    end tell'
done
"""
    else:
        script = f"""#!/bin/bash
for f in "$@"; do
    if [ -d "$f" ]; then
        DIR="$f"
    else
        DIR=$(dirname "$f")
    fi
    osascript -e 'tell application "Terminal"
        activate
        do script "cd '"'"''"$DIR"''"'"' && {cmux_path} {cmux_command}"
    end tell'
done
"""

    # Write the shell script
    script_path = contents_dir / "document.wflow"

    # Create the Info.plist
    info_plist = {
        "NSServices": [
            {
                "NSMenuItem": {"default": name.replace(".workflow", "")},
                "NSMessage": "runWorkflowAsService",
            }
        ],
    }
    plist_path = contents_dir / "Info.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(info_plist, f)

    # Create the actual Automator workflow XML (document.wflow)
    # This is a plist that defines a "Run Shell Script" action
    wflow = {
        "AMCanTabToFocus": False,
        "AMTagTabViewSelectedIndex": 0,
        "actions": [
            {
                "action": {
                    "AMAccepts": {
                        "Container": "List",
                        "Optional": True,
                        "Types": ["com.apple.cocoa.path"],
                    },
                    "AMActionVersion": "2.0.3",
                    "AMApplication": ["Automator"],
                    "AMBundleIdentifier": "com.apple.RunShellScript-TMAction",
                    "AMCategory": "AMCategoryUtilities",
                    "AMIconName": "TerminalIcon",
                    "AMKeyEquivalent": "",
                    "AMParameterProperties": {
                        "COMMAND_STRING": {},
                        "CheckedForUserDefaultShell": {},
                        "inputMethod": {},
                        "shell": {},
                        "source": {},
                    },
                    "AMProvides": {
                        "Container": "List",
                        "Types": ["com.apple.cocoa.string"],
                    },
                    "AMRequiredResources": [],
                    "AMTag": "Run Shell Script",
                    "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
                    "ActionName": "Run Shell Script",
                    "ActionParameters": {
                        "COMMAND_STRING": script,
                        "CheckedForUserDefaultShell": True,
                        "inputMethod": 1,
                        "shell": "/bin/bash",
                        "source": "",
                    },
                    "BundleIdentifier": "com.apple.RunShellScript-TMAction",
                    "CFBundleVersion": "2.0.3",
                    "CanShowSelectedItemsWhenRun": True,
                    "CanShowWhenRun": True,
                    "Category": ["AMCategoryUtilities"],
                    "Class Name": "RunShellScriptAction",
                    "InputUUID": "0",
                    "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
                    "OutputUUID": "0",
                    "UUID": "0",
                    "UnlocalizedApplications": ["Automator"],
                },
                "isViewVisible": True,
            }
        ],
        "connectors": {},
        "workflowMetaData": {
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }

    with open(script_path, "wb") as f:
        plistlib.dump(wflow, f)

    return workflow_dir


def install_context_menu() -> None:
    """Install macOS Finder Quick Actions for cmux."""
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)

    try:
        start_wf = _create_workflow(WORKFLOW_NAME_START, "start")
        console.print(f"[green]Created:[/green] {start_wf}")

        dash_wf = _create_workflow(WORKFLOW_NAME_DASHBOARD, "dashboard")
        console.print(f"[green]Created:[/green] {dash_wf}")

        # Reset the services menu cache
        subprocess.run(
            ["/System/Library/CoreServices/pbs", "-flush"],
            capture_output=True,
        )

        console.print("\n[green]Finder Quick Actions installed![/green]")
        console.print("Right-click any folder in Finder → Quick Actions → 'Open cmux here'")
        console.print("You may need to enable them in System Settings → Extensions → Finder.")
    except Exception as e:
        console.print(f"[red]Failed to install Quick Actions:[/red] {e}")


def uninstall_context_menu() -> None:
    """Remove macOS Finder Quick Actions for cmux."""
    removed = 0
    for name in [WORKFLOW_NAME_START, WORKFLOW_NAME_DASHBOARD]:
        path = SERVICES_DIR / name
        if path.exists():
            shutil.rmtree(path)
            console.print(f"[green]Removed:[/green] {path}")
            removed += 1

    if removed:
        subprocess.run(
            ["/System/Library/CoreServices/pbs", "-flush"],
            capture_output=True,
        )
        console.print("[green]Quick Actions removed.[/green]")
    else:
        console.print("[dim]No cmux Quick Actions found to remove.[/dim]")

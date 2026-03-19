"""Config loading for cmux (~/.cmux/config.yaml)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from cmux.tasks.models import CmuxConfig

CMUX_HOME = Path.home() / ".cmux"
CONFIG_FILE = CMUX_HOME / "config.yaml"
TEMPLATES_DIR = CMUX_HOME / "templates"
SKILLS_DIR = CMUX_HOME / "skills"
DATA_DIR = CMUX_HOME / "data"
TASKS_FILE = CMUX_HOME / "tasks.yaml"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def ensure_dirs() -> None:
    """Create cmux directories if they don't exist."""
    for d in [CMUX_HOME, TEMPLATES_DIR, SKILLS_DIR, DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config() -> CmuxConfig:
    """Load config from ~/.cmux/config.yaml, falling back to defaults."""
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        return CmuxConfig(**data)
    return CmuxConfig()


def save_config(config: CmuxConfig) -> None:
    """Save config to ~/.cmux/config.yaml."""
    ensure_dirs()
    data = config.model_dump(mode="json")
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def read_claude_settings() -> dict:
    """Read .claude/settings.json to discover MCP servers."""
    if CLAUDE_SETTINGS.exists():
        with open(CLAUDE_SETTINGS) as f:
            return json.load(f)
    return {}


def get_mcp_servers() -> list[str]:
    """Return list of MCP server names from Claude settings."""
    settings = read_claude_settings()
    return list(settings.get("mcpServers", {}).keys())


def upsert_claude_mcp_command_server(
    server_name: str,
    command: str,
    args: list[str] | None = None,
    tools: list[str] | None = None,
) -> None:
    """Create or update a Claude MCP command server entry in ~/.claude/settings.json."""
    settings = read_claude_settings()
    mcp_servers = settings.setdefault("mcpServers", {})

    entry: dict[str, object] = {
        "command": command,
        "args": args or [],
    }
    if tools:
        entry["tools"] = tools

    mcp_servers[server_name] = entry

    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAUDE_SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)


def upsert_claude_mcp_http_server(server_name: str, server_url: str) -> None:
    """Create or update a Claude MCP HTTP server entry in ~/.claude/settings.json."""
    settings = read_claude_settings()
    mcp_servers = settings.setdefault("mcpServers", {})
    mcp_servers[server_name] = {
        "transport": "http",
        "url": server_url,
    }

    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAUDE_SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)

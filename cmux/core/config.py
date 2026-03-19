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
    """Read .claude/settings.json to discover MCP servers. Never writes to it."""
    if CLAUDE_SETTINGS.exists():
        with open(CLAUDE_SETTINGS) as f:
            return json.load(f)
    return {}


def get_mcp_servers() -> list[str]:
    """Return list of MCP server names from Claude settings."""
    settings = read_claude_settings()
    return list(settings.get("mcpServers", {}).keys())

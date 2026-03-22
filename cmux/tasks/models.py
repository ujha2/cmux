"""Pydantic models for cmux tasks, skills, config, and session status."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    LAUNCHING = "launching"
    RUNNING = "running"
    IDLE = "idle"
    DONE = "done"
    ERROR = "error"


class TaskType(str, Enum):
    AGENT = "agent"
    HUMAN = "human"


class OutputFormat(str, Enum):
    MARKDOWN = "md"
    DOCX = "docx"
    PPTX = "pptx"
    CODE = "code"
    CSV = "csv"
    JSON = "json"
    EMAIL = "email"
    IMAGES = "images"


class SkillDef(BaseModel):
    """Definition of a PM skill."""

    name: str
    description: str
    prompt_template: str
    output_formats: list[OutputFormat] = [OutputFormat.MARKDOWN]
    tools: list[str] = Field(default_factory=list)
    template_files: list[str] = Field(default_factory=list)
    time_estimate_manual_minutes: int = 60
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class Task(BaseModel):
    """A task to be executed by an AI session."""

    id: str = ""
    name: str
    description: str
    skill: str | None = None
    source: str = "interactive"
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_dir: Path | None = None
    output_files: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    task_type: TaskType = TaskType.AGENT
    priority: int = 0


class BackendConfig(BaseModel):
    backend: str = "claude"
    claude_model: str = "claude-sonnet-4-6"
    claude_args: list[str] = Field(default_factory=list)


class DashboardConfig(BaseModel):
    time_saved_multiplier: dict[str, float] = Field(default_factory=dict)


class PresetConfig(BaseModel):
    name: str
    description: str = ""
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    auto_start: bool = True


class CmuxConfig(BaseModel):
    """Top-level cmux configuration."""

    backend: BackendConfig = Field(default_factory=BackendConfig)
    max_parallel_sessions: int = 5
    output_dir: Path = Path("./cmux-output")
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    template_skill_map: dict[str, list[str]] = Field(default_factory=dict)
    presets: dict[str, PresetConfig] = Field(default_factory=dict)
    workiq_mcp_server: str | None = None
    workiq_tenant_id: str | None = None
    workiq_account: str | None = None
    workiq_registered: bool = False


class TaskHistory(BaseModel):
    """Record of a completed task for stats tracking."""

    task_id: str
    task_name: str
    skill: str
    started_at: datetime
    completed_at: datetime
    status: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    output_file_count: int = 0
    output_total_bytes: int = 0
    time_saved_minutes: float = 0.0

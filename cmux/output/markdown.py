"""Markdown output handler."""

from __future__ import annotations

from pathlib import Path


def save_markdown(content: str, output_dir: Path, filename_base: str) -> Path:
    """Save content as a Markdown file."""
    path = output_dir / f"{filename_base}.md"
    path.write_text(content)
    return path

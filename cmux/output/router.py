"""Smart output format routing — maps skills to output handlers."""

from __future__ import annotations

from pathlib import Path

from cmux.output.markdown import save_markdown
from cmux.output.office import save_docx, save_pptx
from cmux.tasks.models import OutputFormat


def route_output(
    content: str,
    output_dir: Path,
    filename_base: str,
    formats: list[OutputFormat],
) -> list[Path]:
    """Route content to the appropriate output format(s). Returns paths of created files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []

    for fmt in formats:
        if fmt == OutputFormat.MARKDOWN:
            path = save_markdown(content, output_dir, filename_base)
            created.append(path)
        elif fmt == OutputFormat.DOCX:
            path = save_docx(content, output_dir, filename_base)
            created.append(path)
        elif fmt == OutputFormat.PPTX:
            path = save_pptx(content, output_dir, filename_base)
            created.append(path)
        elif fmt == OutputFormat.CSV:
            path = output_dir / f"{filename_base}.csv"
            path.write_text(content)
            created.append(path)
        elif fmt == OutputFormat.JSON:
            path = output_dir / f"{filename_base}.json"
            path.write_text(content)
            created.append(path)
        elif fmt in (OutputFormat.CODE, OutputFormat.EMAIL, OutputFormat.IMAGES):
            # Code/email/images are handled directly by the AI backend
            path = save_markdown(content, output_dir, filename_base)
            created.append(path)

    if not created:
        path = save_markdown(content, output_dir, filename_base)
        created.append(path)

    return created

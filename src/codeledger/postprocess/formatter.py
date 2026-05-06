"""Markdown formatter — applies consistent formatting and injects metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

import codeledger

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def format_doc(
    content: str,
    doc_id: str,
    project_name: str,
    model_name: str,
    session_type: str,
    files_analyzed: int,
    input_tokens: int,
    output_tokens: int,
) -> str:
    """Format a generated document with metadata header and consistent structure.

    Args:
        content: Raw AI-generated markdown content.
        doc_id: Document identifier (e.g., "pd_001").
        project_name: Name of the project.
        model_name: Name of the model that generated this.
        session_type: Type of session (trivial/minor/standard/major/refactor).
        files_analyzed: Number of files included in the analysis.
        input_tokens: Input tokens used.
        output_tokens: Output tokens used.

    Returns:
        Formatted markdown string with metadata header.
    """
    template_path = TEMPLATE_DIR / "doc_template.md.j2"
    template_str = template_path.read_text(encoding="utf-8")
    template = Template(template_str)

    # Parse the AI content into sections
    sections = _extract_sections(content)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rendered = template.render(
        version=codeledger.__version__,
        timestamp=timestamp,
        model_name=model_name,
        session_type=session_type,
        files_analyzed=files_analyzed,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        doc_id=doc_id,
        project_name=project_name,
        sections=sections,
    )

    return rendered


def format_merge_doc(
    content: str,
    project_name: str,
    model_name: str,
    docs_merged: int,
) -> str:
    """Format a merged documentation file."""
    template_path = TEMPLATE_DIR / "merge_template.md.j2"
    template_str = template_path.read_text(encoding="utf-8")
    template = Template(template_str)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rendered = template.render(
        version=codeledger.__version__,
        timestamp=timestamp,
        model_name=model_name,
        docs_merged=docs_merged,
        total_phases=docs_merged,
        project_name=project_name,
        content=content,
    )

    return rendered


def _extract_sections(content: str) -> list[dict]:
    """Extract sections from AI-generated markdown.

    Splits content on ## headings into named sections.
    """
    import re

    sections = []
    parts = re.split(r"^(##\s+.+)$", content, flags=re.MULTILINE)

    # parts alternates: [preamble, heading1, body1, heading2, body2, ...]
    i = 1  # skip preamble
    while i < len(parts) - 1:
        heading = parts[i].lstrip("# ").strip()
        body = parts[i + 1].strip()
        sections.append({"name": heading, "content": body})
        i += 2

    # If no sections found, treat the whole thing as one section
    if not sections and content.strip():
        sections.append({"name": "Documentation", "content": content.strip()})

    return sections

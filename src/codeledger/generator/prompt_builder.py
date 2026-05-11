"""Prompt builder — assembles complete prompts from template + compressed payload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codeledger.classifier.session import SessionType
from codeledger.config.schema import TemplateSectionConfig

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "prompt_templates"


def _load_system_prompt(session_type: SessionType) -> str:
    """Load the system prompt template for a given session type."""
    template_map = {
        SessionType.TRIVIAL: "micro.txt",
        SessionType.MINOR: "micro.txt",
        SessionType.STANDARD: "standard.txt",
        SessionType.MAJOR: "standard.txt",
        SessionType.REFACTOR: "refactor.txt",
    }

    template_file = TEMPLATES_DIR / template_map[session_type]
    return template_file.read_text(encoding="utf-8")


def _load_merge_prompt() -> str:
    """Load the merge/conceptualization system prompt."""
    return (TEMPLATES_DIR / "merge.txt").read_text(encoding="utf-8")


def build_sections_directive(sections: list[TemplateSectionConfig]) -> str:
    """Build the sections directive telling the model what to generate."""
    lines = ["Generate the following sections:"]
    for i, section in enumerate(sections, 1):
        depth_note = f" (depth: {section.depth.value})" if section.depth else ""
        lines.append(
            f"{i}. **{section.name}** (id: {section.id}, "
            f"format: {section.format.value}{depth_note})"
        )
    return "\n".join(lines)


def build_generation_prompt(
    compressed_payload: list[dict[str, Any]],
    sections: list[TemplateSectionConfig],
    session_type: SessionType,
    project_name: str = "Project",
    focus_highlights: list[str] | None = None,
    deferred_summaries: list[str] | None = None,
) -> tuple[str, str]:
    """Build the complete prompt for documentation generation.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = _load_system_prompt(session_type)

    # Build user prompt
    parts: list[str] = []

    parts.append(f"# Project: {project_name}\n")

    # Sections directive
    parts.append(build_sections_directive(sections))
    parts.append("")

    # Focus highlights
    if focus_highlights:
        parts.append("## Focus Areas")
        parts.append("Pay special attention to these files:")
        for h in focus_highlights:
            parts.append(f"- `{h}`")
        parts.append("")

    # Deferred changes context
    if deferred_summaries:
        parts.append("## Previously Deferred Changes")
        parts.append("The following small changes were deferred from earlier sessions:")
        for s in deferred_summaries:
            parts.append(f"- {s}")
        parts.append("Integrate these into the current documentation.\n")

    # The payload
    parts.append("## Project Structure (Compressed)")
    parts.append("```yaml")
    parts.append(json.dumps(compressed_payload, indent=2))
    parts.append("```")

    user_prompt = "\n".join(parts)

    return system_prompt, user_prompt


def build_merge_prompt(
    doc_summaries: list[dict[str, Any]],
    project_name: str = "Project",
) -> tuple[str, str]:
    """Build the prompt for merging multiple docs into a final document.

    Args:
        doc_summaries: List of compressed representations of each doc.
        project_name: Name of the project.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    system_prompt = _load_merge_prompt()

    parts: list[str] = []
    parts.append(f"# Project: {project_name}\n")
    parts.append(f"Merge the following {len(doc_summaries)} documentation snapshots:\n")

    for i, summary in enumerate(doc_summaries, 1):
        parts.append(f"## Snapshot {i}")
        parts.append("```yaml")
        parts.append(json.dumps(summary, indent=2))
        parts.append("```\n")

    user_prompt = "\n".join(parts)

    return system_prompt, user_prompt

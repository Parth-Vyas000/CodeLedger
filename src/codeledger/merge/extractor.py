"""Section extractor — parses generated docs into structured sections for merge."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ExtractedSection:
    """A single section extracted from a generated document."""

    heading: str
    content: str
    doc_id: str
    section_id: str | None = None  # matched config section id

    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass
class ExtractedDoc:
    """A fully parsed generated document with its sections."""

    doc_id: str
    session_type: str
    timestamp: str
    sections: list[ExtractedSection] = field(default_factory=list)

    def get_section(self, heading: str) -> ExtractedSection | None:
        heading_lower = heading.lower()
        for s in self.sections:
            if heading_lower in s.heading.lower() or s.heading.lower() in heading_lower:
                return s
        return None


# Mapping of common heading keywords to section IDs from config schema
_HEADING_TO_ID: dict[str, str] = {
    "phase": "status",
    "execution": "status",
    "summary": "status",
    "architecture": "architecture",
    "structure": "architecture",
    "decision": "decisions",
    "rationale": "decisions",
    "component": "logic",
    "logic": "logic",
    "integration": "data_flow",
    "data flow": "data_flow",
    "flow": "data_flow",
    "edge case": "edge_cases",
    "error": "edge_cases",
    "interview": "interview",
    "learning": "interview",
    "debt": "debt",
    "technical debt": "debt",
    "reference": "commands",
    "quick reference": "commands",
    "command": "commands",
}


def _match_section_id(heading: str) -> str | None:
    """Try to match a heading to a known section ID."""
    heading_lower = heading.lower()
    for keyword, section_id in _HEADING_TO_ID.items():
        if keyword in heading_lower:
            return section_id
    return None


def extract_sections(content: str, doc_id: str) -> list[ExtractedSection]:
    """Extract sections from a markdown document.

    Splits on ## headings and returns structured sections.
    """
    sections: list[ExtractedSection] = []

    # Strip YAML frontmatter if present
    content = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)

    parts = re.split(r"^(##\s+.+)$", content, flags=re.MULTILINE)

    i = 1  # skip preamble
    while i < len(parts) - 1:
        heading = parts[i].lstrip("# ").strip()
        body = parts[i + 1].strip()

        if body:  # skip empty sections
            sections.append(
                ExtractedSection(
                    heading=heading,
                    content=body,
                    doc_id=doc_id,
                    section_id=_match_section_id(heading),
                )
            )
        i += 2

    return sections


def extract_doc(content: str, doc_id: str) -> ExtractedDoc:
    """Parse a full document into an ExtractedDoc.

    Extracts metadata from YAML frontmatter if present.
    """
    session_type = "standard"
    timestamp = ""

    # Try to extract metadata from YAML frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        st_match = re.search(r"session_type:\s*(.+)", fm)
        ts_match = re.search(r"generated:\s*(.+)", fm)
        if st_match:
            session_type = st_match.group(1).strip()
        if ts_match:
            timestamp = ts_match.group(1).strip()

    sections = extract_sections(content, doc_id)

    return ExtractedDoc(
        doc_id=doc_id,
        session_type=session_type,
        timestamp=timestamp,
        sections=sections,
    )

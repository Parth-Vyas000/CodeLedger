"""Deduplicator — resolves overlapping/conflicting sections across docs."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from codeledger.merge.extractor import ExtractedSection


@dataclass
class MergedSection:
    """A section after deduplication and conflict resolution."""

    heading: str
    content: str
    section_id: str | None
    source_doc_ids: list[str] = field(default_factory=list)
    strategy: str = "latest"  # latest | merged | accumulated


def similarity(a: str, b: str) -> float:
    """Compute text similarity ratio between two strings."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def deduplicate_sections(
    section_groups: dict[str, list[ExtractedSection]],
    similarity_threshold: float = 0.85,
) -> list[MergedSection]:
    """Deduplicate and merge sections grouped by section_id.

    Strategy:
    - If only one version exists, keep it.
    - If versions are very similar (>threshold), keep the latest.
    - If versions differ significantly, concatenate with timeline markers.

    Args:
        section_groups: Mapping of section_id (or heading) to list of sections
                        ordered chronologically (oldest first).
        similarity_threshold: Above this, sections are considered duplicates.

    Returns:
        List of merged sections ready for final document.
    """
    merged: list[MergedSection] = []

    for _key, sections in section_groups.items():
        if not sections:
            continue

        if len(sections) == 1:
            s = sections[0]
            merged.append(
                MergedSection(
                    heading=s.heading,
                    content=s.content,
                    section_id=s.section_id,
                    source_doc_ids=[s.doc_id],
                    strategy="latest",
                )
            )
            continue

        # Compare the latest with all previous versions
        latest = sections[-1]
        all_similar = all(
            similarity(s.content, latest.content) > similarity_threshold for s in sections[:-1]
        )

        if all_similar:
            # All versions are essentially the same — keep latest
            merged.append(
                MergedSection(
                    heading=latest.heading,
                    content=latest.content,
                    section_id=latest.section_id,
                    source_doc_ids=[s.doc_id for s in sections],
                    strategy="latest",
                )
            )
        else:
            # Significant evolution — accumulate with timeline markers
            parts: list[str] = []
            for s in sections:
                # Only include meaningfully different versions
                is_unique = not any(
                    similarity(s.content, prev.content) > similarity_threshold
                    for prev in sections
                    if prev is not s and sections.index(prev) > sections.index(s)
                )
                if is_unique or s is latest:
                    parts.append(f"*[{s.doc_id}]*\n\n{s.content}")

            merged.append(
                MergedSection(
                    heading=latest.heading,
                    content="\n\n---\n\n".join(parts),
                    section_id=latest.section_id,
                    source_doc_ids=[s.doc_id for s in sections],
                    strategy="accumulated",
                )
            )

    return merged

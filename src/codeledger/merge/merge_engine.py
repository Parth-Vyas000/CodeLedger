"""Merge engine — orchestrates multi-doc merging into a final conceptualized document."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from codeledger.config.schema import CodeLedgerConfig
from codeledger.generator.model_router import generate
from codeledger.generator.prompt_builder import build_merge_prompt
from codeledger.merge.deduplicator import deduplicate_sections
from codeledger.merge.extractor import ExtractedDoc, ExtractedSection, extract_doc
from codeledger.postprocess.file_manager import load_all_docs, load_manifest, save_manifest
from codeledger.postprocess.formatter import format_merge_doc


def _group_by_section(docs: list[ExtractedDoc]) -> dict[str, list[ExtractedSection]]:
    """Group all sections across docs by their section_id or heading."""
    groups: dict[str, list[ExtractedSection]] = defaultdict(list)

    for doc in docs:
        for section in doc.sections:
            key = section.section_id or section.heading.lower()
            groups[key].append(section)

    return dict(groups)


def _build_doc_summaries(docs: list[ExtractedDoc]) -> list[dict]:
    """Build compressed summaries of each doc for the merge prompt."""
    summaries = []
    for doc in docs:
        sections_data = []
        for s in doc.sections:
            sections_data.append(
                {
                    "heading": s.heading,
                    "words": s.word_count,
                    "content": s.content[:500] if s.word_count > 100 else s.content,
                }
            )
        summaries.append(
            {
                "doc_id": doc.doc_id,
                "session_type": doc.session_type,
                "timestamp": doc.timestamp,
                "sections": sections_data,
            }
        )
    return summaries


def merge_local(
    project_root: Path,
    similarity_threshold: float = 0.85,
) -> str:
    """Merge all docs using local deduplication (no LLM).

    Uses the extractor + deduplicator to combine all generated docs
    into a single merged document. Does not call any AI model.

    Returns the merged markdown content.
    """
    raw_docs = load_all_docs(project_root)
    if not raw_docs:
        return "# No documentation found\n\nRun `codeledger generate` first."

    # Extract sections from all docs
    parsed_docs = [extract_doc(content, doc_id) for doc_id, content in raw_docs]

    # Group sections by type
    section_groups = _group_by_section(parsed_docs)

    # Deduplicate
    merged_sections = deduplicate_sections(section_groups, similarity_threshold)

    # Assemble final document
    parts = [f"# Project Documentation (Merged from {len(raw_docs)} snapshots)\n"]
    for section in merged_sections:
        parts.append(f"## {section.heading}\n")
        parts.append(section.content)
        parts.append("")

    return "\n".join(parts)


def merge_with_llm(
    project_root: Path,
    config: CodeLedgerConfig,
) -> str:
    """Merge all docs using an LLM for conceptualization.

    Sends compressed doc summaries to the model with the merge prompt
    template to produce a coherent final document.

    Returns the formatted merged markdown content.
    """
    raw_docs = load_all_docs(project_root)
    if not raw_docs:
        return "# No documentation found\n\nRun `codeledger generate` first."

    parsed_docs = [extract_doc(content, doc_id) for doc_id, content in raw_docs]
    summaries = _build_doc_summaries(parsed_docs)

    # Build and send merge prompt
    system_prompt, user_prompt = build_merge_prompt(
        doc_summaries=summaries,
        project_name=config.project.name,
    )

    response = generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        config=config.model,
    )

    # Format the output
    formatted = format_merge_doc(
        content=response.content,
        project_name=config.project.name,
        model_name=config.model.model_name,
        docs_merged=len(raw_docs),
    )

    # Update manifest merge state
    manifest = load_manifest(project_root)
    manifest.merge_state = "complete"
    save_manifest(project_root, manifest)

    return formatted

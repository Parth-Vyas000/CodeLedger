"""Scope engine — trims payload and template sections to fit within token budget."""

from __future__ import annotations

from codeledger.compressor.token_compressor import estimate_tokens
from codeledger.config.schema import TemplateSectionConfig


def trim_to_budget(
    compressed_files: list[dict],
    sections: list[TemplateSectionConfig],
    input_token_budget: int,
) -> tuple[list[dict], list[TemplateSectionConfig]]:
    """Trim payload and sections to fit within the input token budget.

    Strategy (applied in order):
    1. Drop affected-only files (keep changed files)
    2. Drop priority 3 sections
    3. Drop priority 2 sections
    4. Truncate individual file descriptions (remove docstrings, globals)
    5. Drop files with fewest changes

    Returns:
        Tuple of (trimmed_files, trimmed_sections).
    """
    current_tokens = estimate_tokens(compressed_files)

    # Estimate section overhead (template text per section)
    section_overhead_per = 50  # ~50 tokens per section in prompt template
    section_tokens = len(sections) * section_overhead_per
    total = current_tokens + section_tokens

    if total <= input_token_budget:
        return compressed_files, sections

    # Step 1: Drop priority 3 sections
    trimmed_sections = [s for s in sections if s.priority <= 2]
    section_tokens = len(trimmed_sections) * section_overhead_per
    total = current_tokens + section_tokens

    if total <= input_token_budget:
        return compressed_files, trimmed_sections

    # Step 2: Drop priority 2 sections
    trimmed_sections = [s for s in trimmed_sections if s.priority <= 1]
    section_tokens = len(trimmed_sections) * section_overhead_per
    total = current_tokens + section_tokens

    if total <= input_token_budget:
        return compressed_files, trimmed_sections

    # Step 3: Strip verbose fields from files
    for f in compressed_files:
        f.pop("module_doc", None)
        f.pop("globals", None)
        for cls in f.get("classes", []):
            cls.pop("doc", None)
        for func in f.get("functions", []):
            func.pop("doc", None)

    current_tokens = estimate_tokens(compressed_files)
    total = current_tokens + section_tokens

    if total <= input_token_budget:
        return compressed_files, trimmed_sections

    # Step 4: Drop files from the end (least important) until within budget
    while compressed_files and total > input_token_budget:
        compressed_files.pop()
        current_tokens = estimate_tokens(compressed_files)
        total = current_tokens + section_tokens

    return compressed_files, trimmed_sections

"""Merge package — multi-doc merging, deduplication, and conceptualization."""

from codeledger.merge.extractor import ExtractedDoc, ExtractedSection, extract_doc
from codeledger.merge.deduplicator import MergedSection, deduplicate_sections
from codeledger.merge.merge_engine import merge_local, merge_with_llm

__all__ = [
    "ExtractedDoc",
    "ExtractedSection",
    "MergedSection",
    "deduplicate_sections",
    "extract_doc",
    "merge_local",
    "merge_with_llm",
]

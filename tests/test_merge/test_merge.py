"""Tests for merge engine."""

from __future__ import annotations

import textwrap

from codeledger.merge.extractor import extract_doc, extract_sections
from codeledger.merge.deduplicator import deduplicate_sections, similarity


class TestExtractor:
    def test_extract_sections(self):
        content = textwrap.dedent("""\
            ## Architecture

            The project uses MVC pattern.

            ## Decisions

            We chose SQLite for simplicity.
        """)
        sections = extract_sections(content, "pd_001")
        assert len(sections) == 2
        assert sections[0].heading == "Architecture"
        assert sections[0].doc_id == "pd_001"
        assert sections[1].heading == "Decisions"

    def test_extract_doc_with_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            session_type: standard
            generated: 2025-01-01 12:00:00 UTC
            ---

            ## Architecture

            MVC pattern.
        """)
        doc = extract_doc(content, "pd_001")
        assert doc.session_type == "standard"
        assert doc.timestamp == "2025-01-01 12:00:00 UTC"
        assert len(doc.sections) == 1

    def test_section_word_count(self):
        content = "## Test\n\nOne two three four five."
        sections = extract_sections(content, "pd_001")
        assert sections[0].word_count == 5

    def test_section_id_matching(self):
        content = "## Code Architecture\n\nSome content."
        sections = extract_sections(content, "pd_001")
        assert sections[0].section_id == "architecture"


class TestDeduplicator:
    def test_similarity_identical(self):
        assert similarity("hello world", "hello world") == 1.0

    def test_similarity_different(self):
        s = similarity("completely different text", "nothing alike here buddy")
        assert s < 0.5

    def test_single_section_kept(self):
        from codeledger.merge.extractor import ExtractedSection

        groups = {
            "architecture": [
                ExtractedSection(
                    heading="Architecture",
                    content="MVC pattern.",
                    doc_id="pd_001",
                    section_id="architecture",
                )
            ]
        }
        result = deduplicate_sections(groups)
        assert len(result) == 1
        assert result[0].strategy == "latest"

    def test_similar_sections_deduped(self):
        from codeledger.merge.extractor import ExtractedSection

        groups = {
            "architecture": [
                ExtractedSection(
                    heading="Architecture",
                    content="The project uses an MVC architecture pattern.",
                    doc_id="pd_001",
                    section_id="architecture",
                ),
                ExtractedSection(
                    heading="Architecture",
                    content="The project uses an MVC architecture pattern.",
                    doc_id="pd_002",
                    section_id="architecture",
                ),
            ]
        }
        result = deduplicate_sections(groups)
        assert len(result) == 1
        assert result[0].strategy == "latest"
        assert "pd_002" in result[0].source_doc_ids

    def test_different_sections_accumulated(self):
        from codeledger.merge.extractor import ExtractedSection

        groups = {
            "architecture": [
                ExtractedSection(
                    heading="Architecture",
                    content="Phase 1: Simple script-based architecture.",
                    doc_id="pd_001",
                    section_id="architecture",
                ),
                ExtractedSection(
                    heading="Architecture",
                    content="Phase 2: Fully refactored to microservices with gRPC.",
                    doc_id="pd_002",
                    section_id="architecture",
                ),
            ]
        }
        result = deduplicate_sections(groups)
        assert len(result) == 1
        assert result[0].strategy == "accumulated"

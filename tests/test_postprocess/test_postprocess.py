"""Tests for post-processing: validator, formatter, file manager."""

from __future__ import annotations

from pathlib import Path

from codeledger.postprocess.validator import validate_output
from codeledger.postprocess.formatter import format_doc, _extract_sections
from codeledger.postprocess.file_manager import (
    Manifest,
    content_hash,
    load_manifest,
    save_doc,
    save_manifest,
)


class TestValidator:
    def test_valid_output(self, sample_markdown: str):
        result = validate_output(
            sample_markdown,
            expected_section_names=["Phase Execution Summary", "Code Architecture"],
        )
        assert result.is_valid
        assert len(result.sections_found) >= 2

    def test_missing_section_warning(self, sample_markdown: str):
        result = validate_output(
            sample_markdown,
            expected_section_names=["Nonexistent Section"],
        )
        assert any(w.category == "missing_section" for w in result.warnings)

    def test_empty_content_fails(self):
        result = validate_output("", expected_section_names=["Anything"])
        assert not result.is_valid

    def test_hallucinated_path_detection(self, sample_markdown: str):
        content = sample_markdown + "\n\nSee `src/nonexistent_file.py` for details.\n"
        result = validate_output(
            content,
            expected_section_names=[],
            known_file_paths={"src/main.py", "src/utils.py"},
        )
        hallucination_warnings = [w for w in result.warnings if w.category == "hallucination"]
        assert len(hallucination_warnings) >= 1


class TestFormatter:
    def test_extract_sections(self, sample_markdown: str):
        sections = _extract_sections(sample_markdown)
        assert len(sections) >= 3
        assert sections[0]["name"] == "Phase Execution Summary"

    def test_format_doc(self, sample_markdown: str):
        formatted = format_doc(
            content=sample_markdown,
            doc_id="pd_001",
            project_name="TestProject",
            model_name="claude-sonnet-4-20250514",
            session_type="standard",
            files_analyzed=5,
            input_tokens=2000,
            output_tokens=3000,
        )
        assert "pd_001" in formatted or "TestProject" in formatted
        assert "codeledger" in formatted.lower()


class TestFileManager:
    def test_content_hash_deterministic(self):
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        assert h1 == h2
        assert len(h1) == 16

    def test_content_hash_differs(self):
        h1 = content_hash("hello")
        h2 = content_hash("world")
        assert h1 != h2

    def test_manifest_next_doc_id(self):
        m = Manifest()
        assert m.next_doc_id() == "pd_001"
        assert m.next_doc_id() == "pd_002"

    def test_save_and_load_manifest(self, tmp_path: Path):
        m = Manifest()
        m.next_doc_id()
        save_manifest(tmp_path, m)

        loaded = load_manifest(tmp_path)
        assert loaded.total_docs == m.total_docs

    def test_save_doc(self, tmp_path: Path):
        m = Manifest()
        doc_id = m.next_doc_id()
        path = save_doc(
            project_root=tmp_path,
            doc_id=doc_id,
            content="# Test Doc\n\nHello.",
            session_type="standard",
            model="test-model",
            files_analyzed=3,
            manifest=m,
        )
        assert path.exists()
        assert m.last_doc_id == doc_id

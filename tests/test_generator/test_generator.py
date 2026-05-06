"""Tests for prompt builder (no API calls)."""

from __future__ import annotations

from codeledger.classifier.session import SessionType
from codeledger.config.schema import DEFAULT_SECTIONS
from codeledger.generator.prompt_builder import (
    build_generation_prompt,
    build_merge_prompt,
    build_sections_directive,
)


class TestPromptBuilder:
    def test_build_sections_directive(self):
        directive = build_sections_directive(DEFAULT_SECTIONS)
        assert "Phase Execution Summary" in directive
        assert "Code Architecture" in directive
        assert "Quick Reference" in directive

    def test_build_generation_prompt_returns_tuple(self):
        payload = [{"path": "main.py", "functions": [{"name": "main"}]}]
        system, user = build_generation_prompt(
            compressed_payload=payload,
            sections=DEFAULT_SECTIONS,
            session_type=SessionType.STANDARD,
            project_name="TestProject",
        )
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert "TestProject" in user
        assert "main.py" in user

    def test_build_generation_prompt_includes_focus(self):
        payload = [{"path": "main.py"}]
        _, user = build_generation_prompt(
            compressed_payload=payload,
            sections=DEFAULT_SECTIONS,
            session_type=SessionType.STANDARD,
            focus_highlights=["src/critical.py"],
        )
        assert "critical.py" in user

    def test_build_merge_prompt(self):
        summaries = [
            {"doc_id": "pd_001", "sections": [{"heading": "Arch", "content": "..."}]},
            {"doc_id": "pd_002", "sections": [{"heading": "Arch", "content": "..."}]},
        ]
        _system, user = build_merge_prompt(summaries, project_name="TestProject")
        assert "TestProject" in user
        assert "pd_001" in user
        assert "Snapshot 1" in user

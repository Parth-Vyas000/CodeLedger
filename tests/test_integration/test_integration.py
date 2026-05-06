"""Integration tests — end-to-end pipeline without API calls."""

from __future__ import annotations

from pathlib import Path

from codeledger.classifier import classify_session
from codeledger.compressor import compress_project, trim_to_budget
from codeledger.config.loader import init_project, load_config
from codeledger.generator.prompt_builder import build_generation_prompt
from codeledger.parser import parse_file
from codeledger.scanner import compare_snapshots, create_snapshot, scan_project
from codeledger.scanner.change_dag import ProjectDAG


class TestPipeline:
    """Test the full analysis pipeline up to prompt generation (no API call)."""

    def test_scan_to_prompt(self, tmp_project: Path):
        """Test scanning → parsing → compressing → prompt building."""
        # Init config
        config = init_project(tmp_project, project_name="test-pipeline")
        config = load_config(tmp_project)

        # Scan
        manifest = scan_project(
            tmp_project,
            include_patterns=config.focus.include_patterns,
            exclude_patterns=config.focus.exclude_patterns,
        )
        assert manifest.total_files > 0

        # Parse
        parsed_files = []
        for fi in manifest.code_files():
            try:
                parsed = parse_file(fi.absolute_path, fi.language or "")
                parsed_files.append(parsed)
            except Exception:
                pass
        assert len(parsed_files) > 0

        # Compress
        compressed = compress_project(parsed_files)
        assert len(compressed) > 0

        # Trim
        trimmed_files, trimmed_sections = trim_to_budget(
            compressed,
            config.template_sections,
            input_token_budget=2000,
        )
        assert len(trimmed_files) > 0

        # Build prompt
        from codeledger.classifier.session import SessionType

        system, user = build_generation_prompt(
            compressed_payload=trimmed_files,
            sections=trimmed_sections,
            session_type=SessionType.STANDARD,
            project_name=config.project.name,
        )
        assert len(system) > 100
        assert "test-pipeline" in user

    def test_snapshot_change_dag_classify(self, tmp_project: Path):
        """Test snapshot → DAG → classification flow."""
        config = init_project(tmp_project, project_name="dag-test")
        config = load_config(tmp_project)

        manifest = scan_project(
            tmp_project,
            include_patterns=config.focus.include_patterns,
            exclude_patterns=config.focus.exclude_patterns,
        )
        s1 = create_snapshot(manifest)

        # Make a change
        (tmp_project / "src" / "utils.py").write_text(
            "def helper(x):\n    return x * 3\n\ndef new_helper():\n    pass\n",
            encoding="utf-8",
        )

        manifest2 = scan_project(
            tmp_project,
            include_patterns=config.focus.include_patterns,
            exclude_patterns=config.focus.exclude_patterns,
        )
        s2 = create_snapshot(manifest2)
        diff = compare_snapshots(s1, s2)

        assert not diff.is_empty

        # Build DAG
        dag = ProjectDAG()
        dag.build(manifest2, tmp_project)
        subgraph = dag.extract_subgraph(diff)

        assert not subgraph.is_empty

        # Classify
        metrics = subgraph.metrics()
        classification = classify_session(metrics)
        assert classification.session_type is not None
        assert classification.confidence > 0

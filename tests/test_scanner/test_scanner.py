"""Tests for file scanner and snapshot engine."""

from __future__ import annotations

from pathlib import Path

from codeledger.scanner.file_scanner import scan_project
from codeledger.scanner.snapshot import (
    compare_snapshots,
    create_snapshot,
    load_latest_snapshot,
    save_snapshot,
)


class TestFileScanner:
    def test_scan_finds_python_files(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])

        assert manifest.total_files > 0
        py_files = manifest.files_by_language("python")
        assert len(py_files) >= 3  # main.py, utils.py, models.py

    def test_scan_respects_exclude_patterns(self, tmp_project: Path):
        # Create a file in an excluded dir
        pycache = tmp_project / "src" / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-310.pyc").write_bytes(b"fake")

        manifest = scan_project(tmp_project, include_patterns=["**/*"])

        paths = [f.path for f in manifest.files]
        assert not any("__pycache__" in p for p in paths)

    def test_scan_counts_lines(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        assert manifest.total_lines > 0

    def test_code_files_filter(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*"])

        code = manifest.code_files()
        all_files = manifest.files
        assert len(code) <= len(all_files)
        assert all(f.is_code() for f in code)

    def test_get_file_by_path(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])

        # Should find at least one file by relative path
        py_file = manifest.code_files()[0]
        found = manifest.get_file(py_file.path)
        assert found is not None
        assert found.path == py_file.path


class TestSnapshot:
    def test_create_snapshot(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        snapshot = create_snapshot(manifest)

        assert len(snapshot.files) > 0
        assert snapshot.snapshot_id

    def test_compare_identical_snapshots(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        s1 = create_snapshot(manifest)
        s2 = create_snapshot(manifest)

        diff = compare_snapshots(s1, s2)
        assert diff.is_empty

    def test_compare_with_changes(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        s1 = create_snapshot(manifest)

        # Modify a file
        (tmp_project / "src" / "utils.py").write_text(
            "def helper(x: int) -> int:\n    return x * 3\n",
            encoding="utf-8",
        )

        manifest2 = scan_project(tmp_project, include_patterns=["**/*.py"])
        s2 = create_snapshot(manifest2)

        diff = compare_snapshots(s1, s2)
        assert not diff.is_empty
        assert diff.files_modified >= 1

    def test_save_and_load_snapshot(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        snapshot = create_snapshot(manifest)

        save_snapshot(tmp_project, snapshot)

        loaded = load_latest_snapshot(tmp_project)
        assert loaded is not None
        assert loaded.snapshot_id == snapshot.snapshot_id
        assert len(loaded.files) == len(snapshot.files)

    def test_detect_new_file(self, tmp_project: Path):
        manifest = scan_project(tmp_project, include_patterns=["**/*.py"])
        s1 = create_snapshot(manifest)

        # Add a new file
        (tmp_project / "src" / "new_module.py").write_text(
            "def new_func():\n    pass\n", encoding="utf-8"
        )

        manifest2 = scan_project(tmp_project, include_patterns=["**/*.py"])
        s2 = create_snapshot(manifest2)

        diff = compare_snapshots(s1, s2)
        assert diff.files_created >= 1
        assert any("new_module" in p for p in diff.created_paths())

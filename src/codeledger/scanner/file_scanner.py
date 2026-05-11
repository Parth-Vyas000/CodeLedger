"""File scanner — walks a project directory, respects ignore patterns, builds file manifest."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pathspec
from pathspec.pattern import Pattern

LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "php": [".php"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".hpp", ".cc", ".hh", ".cxx"],
    "yaml": [".yaml", ".yml"],
    "json": [".json"],
    "toml": [".toml"],
    "markdown": [".md"],
    "sql": [".sql"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
}

_EXT_TO_LANG: dict[str, str] = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        _EXT_TO_LANG[ext] = lang


@dataclass
class FileInfo:
    """Metadata about a single file in the project."""

    path: str  # Relative to project root
    absolute_path: str
    size: int
    lines: int
    language: str | None
    extension: str

    def is_code(self) -> bool:
        """Return True if this is a recognized source code file."""
        return self.language in {
            "python",
            "javascript",
            "typescript",
            "java",
            "go",
            "rust",
            "ruby",
            "php",
            "c",
            "cpp",
        }


@dataclass
class FileManifest:
    """Complete manifest of all files in a project scan."""

    project_root: str
    files: list[FileInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = field(default_factory=dict)  # lang → file count

    def code_files(self) -> list[FileInfo]:
        """Return only source code files."""
        return [f for f in self.files if f.is_code()]

    def files_by_language(self, language: str) -> list[FileInfo]:
        """Return files of a specific language."""
        return [f for f in self.files if f.language == language]

    def get_file(self, relative_path: str) -> FileInfo | None:
        """Look up a file by its relative path."""
        for f in self.files:
            if f.path == relative_path:
                return f
        return None


def detect_language(filepath: Path) -> str | None:
    """Detect the programming language from file extension."""
    return _EXT_TO_LANG.get(filepath.suffix.lower())


def count_lines(filepath: Path) -> int:
    """Count lines in a file. Returns 0 for binary or unreadable files."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def _load_ignore_patterns(project_root: Path) -> list[str]:
    """Load ignore patterns from .gitignore and .codeledgerignore."""
    patterns: list[str] = []

    for ignore_file in [".gitignore", ".codeledgerignore"]:
        ignore_path = project_root / ignore_file
        if ignore_path.exists():
            with open(ignore_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

    return patterns


def _build_pathspec(
    ignore_patterns: list[str],
    exclude_patterns: list[str],
) -> pathspec.PathSpec[Pattern]:  # type: ignore[type-arg]
    """Build a pathspec matcher from ignore + config exclude patterns."""
    all_patterns = ignore_patterns + exclude_patterns
    return pathspec.PathSpec.from_lines("gitwildmatch", all_patterns)


def _matches_include(relative_path: str, include_patterns: list[str]) -> bool:
    """Check if a file matches any include pattern."""
    if not include_patterns:
        return True
    spec = pathspec.PathSpec.from_lines("gitwildmatch", include_patterns)
    return spec.match_file(relative_path)


def scan_project(
    project_root: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> FileManifest:
    """Scan a project directory and build a FileManifest.

    Args:
        project_root: Root directory of the project to scan.
        include_patterns: Glob patterns for files to include (from config).
        exclude_patterns: Glob patterns for files to exclude (from config).

    Returns:
        FileManifest with metadata for all matched files.
    """
    project_root = project_root.resolve()

    if not project_root.is_dir():
        raise NotADirectoryError(f"Not a directory: {project_root}")

    ignore_patterns = _load_ignore_patterns(project_root)
    config_excludes = exclude_patterns or []

    exclude_spec = _build_pathspec(ignore_patterns, config_excludes)
    includes = include_patterns or []

    manifest = FileManifest(project_root=str(project_root))
    lang_counts: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(project_root):
        # Filter out excluded directories in-place for efficiency
        rel_dir = os.path.relpath(dirpath, project_root)
        if rel_dir == ".":
            rel_dir = ""

        filtered_dirs = []
        for d in dirnames:
            dir_rel = os.path.join(rel_dir, d) if rel_dir else d
            # Normalize to forward slashes for pathspec
            dir_rel_normalized = dir_rel.replace(os.sep, "/") + "/"
            if not exclude_spec.match_file(dir_rel_normalized):
                filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        for filename in filenames:
            filepath = Path(dirpath) / filename
            rel_path = os.path.relpath(filepath, project_root).replace(os.sep, "/")

            # Check exclusion
            if exclude_spec.match_file(rel_path):
                continue

            # Check inclusion
            if includes and not _matches_include(rel_path, includes):
                continue

            language = detect_language(filepath)
            lines = count_lines(filepath)

            file_info = FileInfo(
                path=rel_path,
                absolute_path=str(filepath),
                size=filepath.stat().st_size,
                lines=lines,
                language=language,
                extension=filepath.suffix.lower(),
            )
            manifest.files.append(file_info)
            manifest.total_lines += lines

            if language:
                lang_counts[language] = lang_counts.get(language, 0) + 1

    manifest.total_files = len(manifest.files)
    manifest.languages = lang_counts

    return manifest

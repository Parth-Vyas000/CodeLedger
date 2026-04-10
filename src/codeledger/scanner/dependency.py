"""Dependency resolver — builds import graphs from source code."""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Optional

from codeledger.scanner.file_scanner import FileManifest


def resolve_python_imports(filepath: str, project_root: str) -> list[str]:
    """Extract import targets from a Python file.

    Returns a list of module paths that might correspond to project files.
    Ignores standard library and third-party imports (best effort).
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def _module_to_file_candidates(module: str, project_root: str) -> list[str]:
    """Convert a module name to possible file paths within the project.

    For 'src.core.engine', tries:
      - src/core/engine.py
      - src/core/engine/__init__.py
    """
    parts = module.split(".")
    base = os.path.join(*parts)

    candidates = [
        base + ".py",
        os.path.join(base, "__init__.py"),
    ]

    # Also try relative to common source directories
    for src_dir in ["src", "lib", ""]:
        if src_dir:
            for c in [base + ".py", os.path.join(base, "__init__.py")]:
                candidates.append(os.path.join(src_dir, c))

    return [c.replace(os.sep, "/") for c in candidates]


def build_import_graph(
    manifest: FileManifest,
    project_root: Path,
) -> dict[str, set[str]]:
    """Build a file-to-file dependency graph from import statements.

    Args:
        manifest: File manifest from the scanner.
        project_root: Root directory of the project.

    Returns:
        Dict mapping each file (relative path) to the set of files it imports from.
    """
    project_root_str = str(project_root.resolve())
    known_files = {fi.path for fi in manifest.files}

    graph: dict[str, set[str]] = {}

    for fi in manifest.files:
        if fi.language != "python":
            # For MVP, only resolve Python imports
            continue

        imports = resolve_python_imports(fi.absolute_path, project_root_str)
        deps: set[str] = set()

        for module in imports:
            candidates = _module_to_file_candidates(module, project_root_str)
            for candidate in candidates:
                if candidate in known_files and candidate != fi.path:
                    deps.add(candidate)
                    break

        if deps:
            graph[fi.path] = deps

    return graph


def build_reverse_graph(import_graph: dict[str, set[str]]) -> dict[str, set[str]]:
    """Build the reverse dependency graph (who depends on me).

    Args:
        import_graph: Forward graph from build_import_graph.

    Returns:
        Dict mapping each file to the set of files that import it.
    """
    reverse: dict[str, set[str]] = {}

    for source, targets in import_graph.items():
        for target in targets:
            if target not in reverse:
                reverse[target] = set()
            reverse[target].add(source)

    return reverse

"""Shared fixtures for CodeLedger tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from codeledger.config.schema import CodeLedgerConfig


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal temporary project directory with some Python files."""
    # Create source files
    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text(
        textwrap.dedent("""\
        \"\"\"Main entry point.\"\"\"

        from src.utils import helper


        def main():
            result = helper(42)
            print(result)


        if __name__ == "__main__":
            main()
    """),
        encoding="utf-8",
    )

    (src / "utils.py").write_text(
        textwrap.dedent("""\
        \"\"\"Utility functions.\"\"\"


        def helper(x: int) -> int:
            \"\"\"Double the input.\"\"\"
            return x * 2


        def unused_func():
            pass
    """),
        encoding="utf-8",
    )

    (src / "models.py").write_text(
        textwrap.dedent("""\
        \"\"\"Data models.\"\"\"

        from dataclasses import dataclass


        @dataclass
        class User:
            name: str
            email: str

            def display_name(self) -> str:
                return self.name.title()
    """),
        encoding="utf-8",
    )

    # Create a non-code file
    (tmp_path / "README.md").write_text("# Test Project\n", encoding="utf-8")

    # Create a gitignore
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n.venv/\n", encoding="utf-8")

    return tmp_path


@pytest.fixture
def default_config() -> CodeLedgerConfig:
    """Return the default CodeLedger configuration."""
    return CodeLedgerConfig()


@pytest.fixture
def initialized_project(tmp_project: Path) -> Path:
    """Create a project with CodeLedger initialized."""
    from codeledger.config.loader import init_project

    init_project(tmp_project, project_name="test-project")
    return tmp_project


@pytest.fixture
def sample_markdown() -> str:
    """Return sample AI-generated markdown for testing."""
    return textwrap.dedent("""\
        ## Phase Execution Summary

        | Phase | Status | Notes |
        |-------|--------|-------|
        | Setup | Complete | Initial scaffolding done |

        ## Code Architecture

        ```
        src/
          main.py      — entry point
          utils.py     — helper functions
          models.py    — data models
        ```

        ## Decision Rationale

        | Decision | Rationale |
        |----------|-----------|
        | Dataclasses | Simple data containers, no ORM needed |

        ## Component Logic

        The `main()` function delegates to `helper()` for computation.

        ## Quick Reference

        ```bash
        python src/main.py
        ```
    """)

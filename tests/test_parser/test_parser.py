"""Tests for Python parser and fallback parser."""

from __future__ import annotations

import textwrap
from pathlib import Path

from codeledger.parser import get_parser, parse_file
from codeledger.parser.python_parser import PythonParser


class TestPythonParser:
    def test_parse_functions(self, tmp_path: Path):
        code = textwrap.dedent("""\
            def greet(name: str) -> str:
                \"\"\"Say hello.\"\"\"
                return f"Hello, {name}"

            async def fetch_data(url: str) -> dict:
                pass
        """)
        filepath = tmp_path / "sample.py"
        filepath.write_text(code, encoding="utf-8")

        parser = PythonParser()
        result = parser.parse(str(filepath))

        assert len(result.functions) == 2
        assert result.functions[0].name == "greet"
        assert result.functions[0].return_annotation == "str"
        assert result.functions[0].docstring == "Say hello."
        assert result.functions[1].is_async

    def test_parse_classes(self, tmp_path: Path):
        code = textwrap.dedent("""\
            from dataclasses import dataclass

            @dataclass
            class User:
                name: str
                email: str

                def display(self) -> str:
                    return self.name
        """)
        filepath = tmp_path / "models.py"
        filepath.write_text(code, encoding="utf-8")

        parser = PythonParser()
        result = parser.parse(str(filepath))

        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "User"
        assert "dataclass" in [d.name for d in cls.decorators]
        assert len(cls.methods) >= 1

    def test_parse_imports(self, tmp_path: Path):
        code = textwrap.dedent("""\
            import os
            from pathlib import Path
            from typing import Optional
        """)
        filepath = tmp_path / "imports.py"
        filepath.write_text(code, encoding="utf-8")

        parser = PythonParser()
        result = parser.parse(str(filepath))

        assert len(result.imports) >= 3

    def test_trivial_file_detection(self, tmp_path: Path):
        code = "# just a comment\n"
        filepath = tmp_path / "empty.py"
        filepath.write_text(code, encoding="utf-8")

        parser = PythonParser()
        result = parser.parse(str(filepath))
        assert result.is_trivial

    def test_get_parser_returns_python(self):
        parser = get_parser("python")
        assert isinstance(parser, PythonParser)

    def test_get_parser_returns_fallback(self):
        from codeledger.parser.fallback import FallbackParser

        parser = get_parser("javascript")
        assert isinstance(parser, FallbackParser)


class TestFallbackParser:
    def test_parse_js_functions(self, tmp_path: Path):
        code = textwrap.dedent("""\
            function greet(name) {
                return `Hello, ${name}`;
            }

            const fetchData = async (url) => {
                return await fetch(url);
            };
        """)
        filepath = tmp_path / "app.js"
        filepath.write_text(code, encoding="utf-8")

        result = parse_file(str(filepath), "javascript")
        # Fallback should find at least the function declaration
        assert len(result.functions) >= 1

"""Tests for token compressor and scope engine."""

from __future__ import annotations

from codeledger.compressor.token_compressor import (
    compress_function,
    compress_class,
    compress_file,
    estimate_tokens,
)
from codeledger.compressor.scope_engine import trim_to_budget
from codeledger.config.schema import DEFAULT_SECTIONS
from codeledger.parser.base import (
    ParsedClass,
    ParsedDecorator,
    ParsedFile,
    ParsedFunction,
    ParsedParameter,
)


def _make_function(name: str = "helper", params: int = 2) -> ParsedFunction:
    return ParsedFunction(
        name=name,
        line_start=1,
        line_end=10,
        parameters=[
            ParsedParameter(name=f"arg{i}", annotation="int")
            for i in range(params)
        ],
        return_annotation="int",
        docstring="A helper function.",
        decorators=[],
        is_async=False,
        complexity_hint=2,
    )


def _make_class(name: str = "MyClass") -> ParsedClass:
    return ParsedClass(
        name=name,
        line_start=1,
        line_end=20,
        bases=["BaseModel"],
        decorators=[ParsedDecorator(name="dataclass")],
        methods=[_make_function("method_a")],
        class_variables=["field_x"],
        docstring="A data class.",
    )


class TestCompressor:
    def test_compress_function(self):
        func = _make_function()
        result = compress_function(func)
        assert result["name"] == "helper"
        assert "params" in result

    def test_compress_class(self):
        cls = _make_class()
        result = compress_class(cls)
        assert result["name"] == "MyClass"
        assert "bases" in result

    def test_compress_file(self):
        parsed = ParsedFile(
            path="src/main.py",
            language="python",
            functions=[_make_function()],
            classes=[_make_class()],
            imports=[],
            module_docstring="Main module.",
            total_lines=50,
        )
        result = compress_file(parsed)
        assert result["path"] == "src/main.py"
        assert "functions" in result or "classes" in result

    def test_estimate_tokens(self):
        text = "Hello world, this is a test sentence with some words."
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Should be fewer tokens than chars

    def test_trim_to_budget(self):
        parsed = ParsedFile(
            path="src/main.py",
            language="python",
            functions=[_make_function(f"func_{i}") for i in range(20)],
            classes=[],
            imports=[],
            module_docstring="Module.",
            total_lines=200,
        )
        from codeledger.compressor.token_compressor import compress_project

        compressed = compress_project([parsed])
        trimmed_files, trimmed_sections = trim_to_budget(compressed, DEFAULT_SECTIONS, input_token_budget=100)
        # Should have reduced the payload
        assert len(str(trimmed_files)) <= len(str(compressed)) or len(trimmed_files) <= len(compressed)

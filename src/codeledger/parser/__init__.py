"""Parser package — language-specific code analysis."""

from codeledger.parser.base import (
    BaseParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedParameter,
)
from codeledger.parser.python_parser import PythonParser
from codeledger.parser.fallback import FallbackParser


def get_parser(language: str) -> BaseParser:
    """Get the appropriate parser for a language."""
    if language == "python":
        return PythonParser()
    return FallbackParser()


def parse_file(filepath: str, language: str) -> ParsedFile:
    """Parse a file using the appropriate language parser."""
    parser = get_parser(language)
    return parser.parse(filepath)


__all__ = [
    "BaseParser",
    "FallbackParser",
    "ParsedClass",
    "ParsedFile",
    "ParsedFunction",
    "ParsedImport",
    "ParsedParameter",
    "PythonParser",
    "get_parser",
    "parse_file",
]

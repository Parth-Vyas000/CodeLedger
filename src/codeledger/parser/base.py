"""Base parser interface — abstract base for all language-specific AST parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedParameter:
    """A function/method parameter."""

    name: str
    annotation: str | None = None
    default: str | None = None


@dataclass
class ParsedDecorator:
    """A decorator on a function or class."""

    name: str
    arguments: list[str] = field(default_factory=list)


@dataclass
class ParsedFunction:
    """Parsed representation of a function or method."""

    name: str
    line_start: int
    line_end: int
    parameters: list[ParsedParameter] = field(default_factory=list)
    return_annotation: str | None = None
    decorators: list[ParsedDecorator] = field(default_factory=list)
    docstring: str | None = None
    is_async: bool = False
    is_method: bool = False
    is_property: bool = False
    is_staticmethod: bool = False
    is_classmethod: bool = False
    complexity_hint: int = 0  # rough cyclomatic complexity estimate

    @property
    def signature(self) -> str:
        """Human-readable function signature."""
        params = ", ".join(
            p.name + (f": {p.annotation}" if p.annotation else "") for p in self.parameters
        )
        ret = f" -> {self.return_annotation}" if self.return_annotation else ""
        prefix = "async " if self.is_async else ""
        return f"{prefix}def {self.name}({params}){ret}"


@dataclass
class ParsedClass:
    """Parsed representation of a class."""

    name: str
    line_start: int
    line_end: int
    bases: list[str] = field(default_factory=list)
    decorators: list[ParsedDecorator] = field(default_factory=list)
    methods: list[ParsedFunction] = field(default_factory=list)
    docstring: str | None = None
    class_variables: list[str] = field(default_factory=list)

    @property
    def method_names(self) -> list[str]:
        return [m.name for m in self.methods]

    @property
    def public_methods(self) -> list[ParsedFunction]:
        return [m for m in self.methods if not m.name.startswith("_")]


@dataclass
class ParsedImport:
    """A parsed import statement."""

    module: str
    names: list[str] = field(default_factory=list)  # specific names imported
    is_from: bool = False
    alias: str | None = None


@dataclass
class ParsedFile:
    """Complete parsed representation of a source file."""

    path: str
    language: str
    functions: list[ParsedFunction] = field(default_factory=list)
    classes: list[ParsedClass] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    module_docstring: str | None = None
    global_variables: list[str] = field(default_factory=list)
    total_lines: int = 0
    has_entry_point: bool = False  # e.g., if __name__ == "__main__"

    @property
    def all_functions(self) -> list[ParsedFunction]:
        """All functions including class methods."""
        result = list(self.functions)
        for cls in self.classes:
            result.extend(cls.methods)
        return result

    @property
    def function_count(self) -> int:
        return len(self.functions) + sum(len(c.methods) for c in self.classes)

    @property
    def is_trivial(self) -> bool:
        """True if file is likely boilerplate (__init__.py, setup.py with no logic)."""
        return self.function_count == 0 and len(self.classes) == 0 and self.total_lines < 20


class BaseParser(ABC):
    """Abstract base class for language-specific AST parsers."""

    @abstractmethod
    def parse(self, filepath: str) -> ParsedFile:
        """Parse a source file and return structured representation."""
        ...

    @abstractmethod
    def supports(self, extension: str) -> bool:
        """Return True if this parser handles the given file extension."""
        ...

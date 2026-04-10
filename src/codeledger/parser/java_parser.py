"""Java parser — regex-based extraction for Java source files."""

from codeledger.parser.fallback import FallbackParser


class JavaParser(FallbackParser):
    """Java parser using regex-based extraction."""

    def supports(self, extension: str) -> bool:
        return extension.lower() == ".java"

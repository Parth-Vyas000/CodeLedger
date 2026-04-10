"""JS/TS parser — regex-based extraction for JavaScript and TypeScript."""

from codeledger.parser.fallback import FallbackParser


class JSParser(FallbackParser):
    """JavaScript/TypeScript parser using regex-based extraction."""

    def supports(self, extension: str) -> bool:
        return extension.lower() in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")

"""Fallback parser — regex-based extraction for unsupported languages."""

from __future__ import annotations

import re
from pathlib import Path

from codeledger.parser.base import (
    BaseParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
)

# Common patterns across languages
FUNCTION_PATTERNS = {
    "javascript": re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
        re.MULTILINE,
    ),
    "typescript": re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)",
        re.MULTILINE,
    ),
    "java": re.compile(
        r"(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)(\w+)\s*\(([^)]*)\)\s*(?:throws\s+\w+)?\s*\{",
        re.MULTILINE,
    ),
    "go": re.compile(
        r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(([^)]*)\)",
        re.MULTILINE,
    ),
    "rust": re.compile(
        r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)",
        re.MULTILINE,
    ),
}

CLASS_PATTERNS = {
    "javascript": re.compile(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{"),
    "typescript": re.compile(
        r"(?:export\s+)?class\s+(\w+)(?:<[^>]*>)?(?:\s+extends\s+(\w+))?(?:\s+implements\s+[\w,\s]+)?\s*\{"
    ),
    "java": re.compile(
        r"(?:public\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+[\w,\s]+)?\s*\{"
    ),
}

IMPORT_PATTERNS = {
    "javascript": re.compile(
        r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))"
    ),
    "typescript": re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"),
    "java": re.compile(r"import\s+([\w.]+)\s*;"),
    "go": re.compile(r"\"([\w./]+)\""),
}

EXT_TO_LANG: dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
}


class FallbackParser(BaseParser):
    """Regex-based parser for languages without dedicated AST support."""

    def supports(self, extension: str) -> bool:
        return extension.lower() in EXT_TO_LANG

    def parse(self, filepath: str) -> ParsedFile:
        path = Path(filepath)
        ext = path.suffix.lower()
        language = EXT_TO_LANG.get(ext, "unknown")

        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ParsedFile(path=filepath, language=language)

        lines = source.split("\n")
        parsed = ParsedFile(
            path=filepath,
            language=language,
            total_lines=len(lines),
        )

        # Extract functions
        func_pattern = FUNCTION_PATTERNS.get(language)
        if func_pattern:
            for match in func_pattern.finditer(source):
                line_num = source[: match.start()].count("\n") + 1
                parsed.functions.append(
                    ParsedFunction(
                        name=match.group(1),
                        line_start=line_num,
                        line_end=line_num,
                    )
                )

        # Extract classes
        class_pattern = CLASS_PATTERNS.get(language)
        if class_pattern:
            for match in class_pattern.finditer(source):
                line_num = source[: match.start()].count("\n") + 1
                bases = (
                    [match.group(2)]
                    if match.lastindex and match.lastindex >= 2 and match.group(2)
                    else []
                )
                parsed.classes.append(
                    ParsedClass(
                        name=match.group(1),
                        line_start=line_num,
                        line_end=line_num,
                        bases=bases,
                    )
                )

        # Extract imports
        import_pattern = IMPORT_PATTERNS.get(language)
        if import_pattern:
            for match in import_pattern.finditer(source):
                module = match.group(1) or (
                    match.group(2) if match.lastindex and match.lastindex >= 2 else ""
                )
                if module:
                    parsed.imports.append(
                        ParsedImport(
                            module=module,
                            is_from=True,
                        )
                    )

        return parsed

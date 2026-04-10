"""Output validator — checks AI-generated documentation for quality and correctness."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ValidationWarning:
    """A warning about potential issues in generated documentation."""

    category: str  # hallucination | missing_section | hedging | format
    message: str
    severity: str = "warning"  # warning | error


@dataclass
class ValidationResult:
    """Result of validating generated documentation."""

    is_valid: bool
    warnings: list[ValidationWarning] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        return sum(1 for w in self.warnings if w.severity == "error")


def validate_output(
    content: str,
    expected_section_names: list[str],
    known_file_paths: Optional[set[str]] = None,
) -> ValidationResult:
    """Validate generated documentation content.

    Checks:
    1. Required sections are present
    2. No hallucinated file paths
    3. Markdown syntax is valid
    4. No excessive hedging language
    """
    result = ValidationResult(is_valid=True)

    if not content or len(content.strip()) < 50:
        result.is_valid = False
        result.warnings.append(ValidationWarning(
            category="format",
            message="Generated content is empty or too short",
            severity="error",
        ))
        return result

    # Check for required sections (look for ## headings)
    headings = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    heading_lower = [h.lower().strip() for h in headings]
    result.sections_found = headings

    for section_name in expected_section_names:
        section_lower = section_name.lower().strip()
        # Fuzzy match: check if the section name appears in any heading
        found = any(
            section_lower in h or h in section_lower
            for h in heading_lower
        )
        if not found:
            result.sections_missing.append(section_name)
            result.warnings.append(ValidationWarning(
                category="missing_section",
                message=f"Expected section '{section_name}' not found in output",
                severity="warning",
            ))

    # Check for hallucinated file paths
    if known_file_paths:
        # Find all file path references in the content
        path_refs = re.findall(r"`([^`]*\.[a-zA-Z]{1,4})`", content)
        for ref in path_refs:
            # Skip common non-file references
            if ref.startswith("http") or ref.startswith("pip ") or "=" in ref:
                continue
            # Check if it looks like a file path
            if "/" in ref or ref.endswith((".py", ".js", ".ts", ".yaml", ".json")):
                # Normalize and check
                normalized = ref.lstrip("./")
                if normalized not in known_file_paths:
                    # Check partial match (just filename)
                    filename = normalized.split("/")[-1]
                    partial_match = any(
                        p.endswith(filename) for p in known_file_paths
                    )
                    if not partial_match:
                        result.warnings.append(ValidationWarning(
                            category="hallucination",
                            message=f"Possible hallucinated file path: `{ref}`",
                            severity="warning",
                        ))

    # Check for excessive hedging
    hedging_patterns = [
        r"\b(might|could|possibly|perhaps|maybe|unclear|uncertain)\b",
    ]
    hedging_count = 0
    for pattern in hedging_patterns:
        hedging_count += len(re.findall(pattern, content, re.IGNORECASE))

    if hedging_count > 10:
        result.warnings.append(ValidationWarning(
            category="hedging",
            message=f"Excessive hedging language detected ({hedging_count} instances). "
                    "The model may be uncertain about the project structure.",
            severity="warning",
        ))

    # Check markdown structure
    if not re.search(r"^#", content, re.MULTILINE):
        result.warnings.append(ValidationWarning(
            category="format",
            message="No markdown headings found — output may not be properly structured",
            severity="warning",
        ))

    return result

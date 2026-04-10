"""Session types and classification interface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from codeledger.scanner.change_dag import ChangeMetrics


class SessionType(str, Enum):
    TRIVIAL = "trivial"
    MINOR = "minor"
    STANDARD = "standard"
    MAJOR = "major"
    REFACTOR = "refactor"


@dataclass
class SessionClassification:
    """Result of classifying a development session."""

    session_type: SessionType
    confidence: float  # 0.0 - 1.0
    input_token_budget: int
    output_token_budget: int
    reason: str

    @property
    def should_defer(self) -> bool:
        return self.session_type == SessionType.TRIVIAL


# Token budgets per session type
SESSION_BUDGETS: dict[SessionType, tuple[int, int]] = {
    SessionType.TRIVIAL: (0, 0),        # deferred, no generation
    SessionType.MINOR: (500, 1500),      # micro-doc
    SessionType.STANDARD: (2000, 5000),  # normal doc
    SessionType.MAJOR: (4000, 8000),     # comprehensive doc
    SessionType.REFACTOR: (1500, 3000),  # refactor-focused doc
}


def classify_session(
    metrics: ChangeMetrics,
    use_slm: bool = False,
) -> SessionClassification:
    """Classify a development session based on change metrics.

    Routes to SLM or rule-based classifier.
    """
    if use_slm:
        try:
            from codeledger.classifier.slm import classify_with_slm
            return classify_with_slm(metrics)
        except ImportError:
            pass  # Fall through to rules

    from codeledger.classifier.rules import classify_with_rules
    return classify_with_rules(metrics)

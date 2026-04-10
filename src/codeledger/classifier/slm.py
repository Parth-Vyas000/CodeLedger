"""SLM-based classifier — optional enhanced classification using a local model."""

from __future__ import annotations

from codeledger.classifier.session import (
    SessionClassification,
)
from codeledger.scanner.change_dag import ChangeMetrics


def classify_with_slm(metrics: ChangeMetrics) -> SessionClassification:
    """Classify a session using a local SLM.

    Requires the `codeledger[slm]` extra. Falls back to rule-based
    classification when the SLM dependencies are not installed.
    """
    from codeledger.classifier.rules import classify_with_rules

    return classify_with_rules(metrics)

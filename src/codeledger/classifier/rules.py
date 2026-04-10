"""Rule-based session classifier — MVP classifier using configurable thresholds."""

from __future__ import annotations

from codeledger.classifier.session import (
    SESSION_BUDGETS,
    SessionClassification,
    SessionType,
)
from codeledger.scanner.change_dag import ChangeMetrics


def classify_with_rules(
    metrics: ChangeMetrics,
    trivial_max_files: int = 2,
    trivial_max_lines: int = 30,
    minor_max_files: int = 5,
    minor_max_lines: int = 150,
    standard_max_files: int = 15,
    standard_max_lines: int = 500,
) -> SessionClassification:
    """Classify a session using rule-based thresholds.

    Decision order:
    1. Refactor detection (deletes + creates with low net change)
    2. Trivial (very small changes)
    3. Minor / Standard / Major (by size)
    """
    net_lines = metrics.lines_added + metrics.lines_removed

    # --- Refactor detection ---
    if (
        metrics.files_deleted > 0
        and metrics.new_files_created > 0
        and abs(metrics.net_lines) < 50
        and metrics.files_changed >= 3
    ):
        budgets = SESSION_BUDGETS[SessionType.REFACTOR]
        return SessionClassification(
            session_type=SessionType.REFACTOR,
            confidence=0.85,
            input_token_budget=budgets[0],
            output_token_budget=budgets[1],
            reason=(
                f"Refactor detected: {metrics.files_deleted} deleted, "
                f"{metrics.new_files_created} created, "
                f"low net line change ({metrics.net_lines})"
            ),
        )

    # --- Trivial ---
    if (
        metrics.files_changed <= trivial_max_files
        and net_lines <= trivial_max_lines
        and metrics.new_files_created == 0
        and not metrics.has_structural_changes
    ):
        budgets = SESSION_BUDGETS[SessionType.TRIVIAL]
        return SessionClassification(
            session_type=SessionType.TRIVIAL,
            confidence=0.90,
            input_token_budget=budgets[0],
            output_token_budget=budgets[1],
            reason=(
                f"Trivial: {metrics.files_changed} files, "
                f"{net_lines} lines changed"
            ),
        )

    # --- Minor ---
    if (
        metrics.files_changed <= minor_max_files
        and net_lines <= minor_max_lines
    ):
        budgets = SESSION_BUDGETS[SessionType.MINOR]
        return SessionClassification(
            session_type=SessionType.MINOR,
            confidence=0.85,
            input_token_budget=budgets[0],
            output_token_budget=budgets[1],
            reason=(
                f"Minor: {metrics.files_changed} files, "
                f"{net_lines} lines changed"
            ),
        )

    # --- Standard ---
    if (
        metrics.files_changed <= standard_max_files
        and net_lines <= standard_max_lines
    ):
        budgets = SESSION_BUDGETS[SessionType.STANDARD]
        return SessionClassification(
            session_type=SessionType.STANDARD,
            confidence=0.85,
            input_token_budget=budgets[0],
            output_token_budget=budgets[1],
            reason=(
                f"Standard: {metrics.files_changed} files, "
                f"{net_lines} lines changed"
            ),
        )

    # --- Major ---
    budgets = SESSION_BUDGETS[SessionType.MAJOR]
    return SessionClassification(
        session_type=SessionType.MAJOR,
        confidence=0.80,
        input_token_budget=budgets[0],
        output_token_budget=budgets[1],
        reason=(
            f"Major: {metrics.files_changed} files, "
            f"{net_lines} lines changed, "
            f"{metrics.new_files_created} new files"
        ),
    )

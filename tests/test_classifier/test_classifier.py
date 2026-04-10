"""Tests for session classifier."""

from __future__ import annotations

from codeledger.classifier.rules import classify_with_rules
from codeledger.classifier.session import SessionType, classify_session
from codeledger.scanner.change_dag import ChangeMetrics


class TestClassifier:
    def test_trivial_classification(self):
        metrics = ChangeMetrics(
            files_changed=1,
            new_files_created=0,
            files_deleted=0,
            lines_added=10,
            lines_removed=5,
            net_lines=5,
            affected_nodes_count=0,
            total_magnitude=0.1,
        )
        result = classify_with_rules(metrics)
        assert result.session_type == SessionType.TRIVIAL

    def test_minor_classification(self):
        metrics = ChangeMetrics(
            files_changed=3,
            new_files_created=1,
            files_deleted=0,
            lines_added=80,
            lines_removed=20,
            net_lines=60,
            affected_nodes_count=2,
            total_magnitude=0.3,
            has_structural_changes=True,
        )
        result = classify_with_rules(metrics)
        assert result.session_type == SessionType.MINOR

    def test_standard_classification(self):
        metrics = ChangeMetrics(
            files_changed=8,
            new_files_created=2,
            files_deleted=0,
            lines_added=300,
            lines_removed=50,
            net_lines=250,
            affected_nodes_count=5,
            total_magnitude=0.5,
            has_structural_changes=True,
        )
        result = classify_with_rules(metrics)
        assert result.session_type == SessionType.STANDARD

    def test_major_classification(self):
        metrics = ChangeMetrics(
            files_changed=20,
            new_files_created=5,
            files_deleted=2,
            lines_added=800,
            lines_removed=200,
            net_lines=600,
            affected_nodes_count=10,
            total_magnitude=0.8,
            has_structural_changes=True,
        )
        result = classify_with_rules(metrics)
        assert result.session_type in (SessionType.MAJOR, SessionType.REFACTOR)

    def test_classify_session_uses_rules_by_default(self):
        metrics = ChangeMetrics(
            files_changed=1,
            new_files_created=0,
            files_deleted=0,
            lines_added=5,
            lines_removed=0,
            net_lines=5,
            affected_nodes_count=0,
            total_magnitude=0.05,
        )
        result = classify_session(metrics, use_slm=False)
        assert result.session_type == SessionType.TRIVIAL
        assert result.confidence > 0

    def test_trivial_should_defer(self):
        metrics = ChangeMetrics(
            files_changed=1,
            new_files_created=0,
            files_deleted=0,
            lines_added=5,
            lines_removed=0,
            net_lines=5,
            affected_nodes_count=0,
            total_magnitude=0.05,
        )
        result = classify_session(metrics)
        assert result.should_defer

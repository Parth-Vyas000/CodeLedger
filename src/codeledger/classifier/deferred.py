"""Deferred change accumulator — buffers trivial sessions until flush threshold."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from codeledger.scanner.change_dag import ChangeMetrics

yaml = YAML()
yaml.default_flow_style = False

PENDING_FILE = ".codeledger/.pending_changes.yaml"


@dataclass
class DeferredSession:
    """Record of a deferred trivial session."""

    session_id: str
    timestamp: str
    files_changed: list[str]
    summary: str
    magnitude: float


@dataclass
class PendingChanges:
    """Accumulated deferred changes waiting to be flushed."""

    pending_sessions: list[DeferredSession] = field(default_factory=list)
    accumulated_magnitude: float = 0.0
    sessions_deferred: int = 0

    def should_flush(
        self,
        flush_threshold: float = 0.40,
        max_deferred: int = 5,
    ) -> bool:
        """Check if accumulated changes should trigger a documentation flush."""
        if self.sessions_deferred >= max_deferred:
            return True
        if self.accumulated_magnitude >= flush_threshold:
            return True
        return False

    def add_session(
        self,
        changed_paths: list[str],
        metrics: ChangeMetrics,
        summary: str = "",
    ) -> None:
        """Add a deferred session to the pending buffer."""
        now = datetime.now(timezone.utc)
        session_id = f"deferred_{now.strftime('%Y%m%d_%H%M%S')}"

        if not summary:
            summary = (
                f"{metrics.files_changed} files, "
                f"{metrics.lines_added}+ / {metrics.lines_removed}- lines"
            )

        session = DeferredSession(
            session_id=session_id,
            timestamp=now.isoformat(),
            files_changed=changed_paths,
            summary=summary,
            magnitude=metrics.total_magnitude,
        )

        self.pending_sessions.append(session)
        self.accumulated_magnitude += metrics.total_magnitude
        self.sessions_deferred += 1

    def flush(self) -> list[DeferredSession]:
        """Flush all pending sessions and return them. Resets the buffer."""
        flushed = list(self.pending_sessions)
        self.pending_sessions = []
        self.accumulated_magnitude = 0.0
        self.sessions_deferred = 0
        return flushed

    def to_dict(self) -> dict:
        return {
            "pending_sessions": [
                {
                    "session_id": s.session_id,
                    "timestamp": s.timestamp,
                    "files_changed": s.files_changed,
                    "summary": s.summary,
                    "magnitude": s.magnitude,
                }
                for s in self.pending_sessions
            ],
            "accumulated_magnitude": round(self.accumulated_magnitude, 4),
            "sessions_deferred": self.sessions_deferred,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PendingChanges":
        sessions = [
            DeferredSession(
                session_id=s["session_id"],
                timestamp=s["timestamp"],
                files_changed=s.get("files_changed", []),
                summary=s.get("summary", ""),
                magnitude=s.get("magnitude", 0.0),
            )
            for s in data.get("pending_sessions", [])
        ]
        return cls(
            pending_sessions=sessions,
            accumulated_magnitude=data.get("accumulated_magnitude", 0.0),
            sessions_deferred=data.get("sessions_deferred", 0),
        )


def load_pending(project_root: Path) -> PendingChanges:
    """Load pending changes from disk."""
    filepath = project_root / PENDING_FILE
    if not filepath.exists():
        return PendingChanges()

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    if not data:
        return PendingChanges()

    return PendingChanges.from_dict(data)


def save_pending(project_root: Path, pending: PendingChanges) -> None:
    """Save pending changes to disk."""
    filepath = project_root / PENDING_FILE
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(pending.to_dict(), f)

"""Snapshot engine — hash-based change detection without requiring git."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from codeledger.scanner.file_scanner import FileManifest

yaml = YAML()
yaml.default_flow_style = False

SNAPSHOT_DIR = ".codeledger/.cache/snapshots"


class ChangeType:
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class FileSnapshot:
    """Hash snapshot of a single file."""

    path: str
    hash: str
    size: int
    lines: int


@dataclass
class FileChange:
    """A detected change between two snapshots."""

    path: str
    change_type: str  # created | modified | deleted
    old_hash: str | None = None
    new_hash: str | None = None
    lines_before: int = 0
    lines_after: int = 0

    @property
    def lines_delta(self) -> int:
        return self.lines_after - self.lines_before


@dataclass
class SnapshotDiff:
    """Difference between two snapshots."""

    changes: list[FileChange] = field(default_factory=list)
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

    @property
    def total_changes(self) -> int:
        return self.files_created + self.files_modified + self.files_deleted

    @property
    def is_empty(self) -> bool:
        return self.total_changes == 0

    def changed_paths(self) -> list[str]:
        """Return all paths that have any change."""
        return [c.path for c in self.changes]

    def created_paths(self) -> list[str]:
        return [c.path for c in self.changes if c.change_type == ChangeType.CREATED]

    def modified_paths(self) -> list[str]:
        return [c.path for c in self.changes if c.change_type == ChangeType.MODIFIED]

    def deleted_paths(self) -> list[str]:
        return [c.path for c in self.changes if c.change_type == ChangeType.DELETED]


@dataclass
class Snapshot:
    """Complete snapshot of a project at a point in time."""

    snapshot_id: str
    timestamp: str
    doc_id: str | None
    files: dict[str, FileSnapshot] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "doc_id": self.doc_id,
            "files": {
                path: {
                    "hash": fs.hash,
                    "size": fs.size,
                    "lines": fs.lines,
                }
                for path, fs in self.files.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        files = {}
        for path, fdata in data.get("files", {}).items():
            files[path] = FileSnapshot(
                path=path,
                hash=fdata["hash"],
                size=fdata["size"],
                lines=fdata["lines"],
            )
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=data["timestamp"],
            doc_id=data.get("doc_id"),
            files=files,
        )


def hash_file(filepath: str) -> str:
    """Compute SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def create_snapshot(
    manifest: FileManifest,
    doc_id: str | None = None,
) -> Snapshot:
    """Create a snapshot from a file manifest by hashing all files."""
    now = datetime.now(timezone.utc)
    snapshot_id = f"snap_{now.strftime('%Y%m%d_%H%M%S')}"

    files: dict[str, FileSnapshot] = {}
    for fi in manifest.files:
        file_hash = hash_file(fi.absolute_path)
        files[fi.path] = FileSnapshot(
            path=fi.path,
            hash=file_hash,
            size=fi.size,
            lines=fi.lines,
        )

    return Snapshot(
        snapshot_id=snapshot_id,
        timestamp=now.isoformat(),
        doc_id=doc_id,
        files=files,
    )


def compare_snapshots(old: Snapshot, new: Snapshot) -> SnapshotDiff:
    """Compare two snapshots and return the diff."""
    diff = SnapshotDiff()

    old_paths = set(old.files.keys())
    new_paths = set(new.files.keys())

    # Created files
    for path in new_paths - old_paths:
        nf = new.files[path]
        diff.changes.append(
            FileChange(
                path=path,
                change_type=ChangeType.CREATED,
                new_hash=nf.hash,
                lines_after=nf.lines,
            )
        )
        diff.files_created += 1
        diff.total_lines_added += nf.lines

    # Deleted files
    for path in old_paths - new_paths:
        of = old.files[path]
        diff.changes.append(
            FileChange(
                path=path,
                change_type=ChangeType.DELETED,
                old_hash=of.hash,
                lines_before=of.lines,
            )
        )
        diff.files_deleted += 1
        diff.total_lines_removed += of.lines

    # Modified files
    for path in old_paths & new_paths:
        of = old.files[path]
        nf = new.files[path]
        if of.hash != nf.hash:
            delta = nf.lines - of.lines
            diff.changes.append(
                FileChange(
                    path=path,
                    change_type=ChangeType.MODIFIED,
                    old_hash=of.hash,
                    new_hash=nf.hash,
                    lines_before=of.lines,
                    lines_after=nf.lines,
                )
            )
            diff.files_modified += 1
            if delta > 0:
                diff.total_lines_added += delta
            else:
                diff.total_lines_removed += abs(delta)

    return diff


def _snapshot_dir(project_root: Path) -> Path:
    return project_root / SNAPSHOT_DIR


def save_snapshot(project_root: Path, snapshot: Snapshot) -> Path:
    """Save a snapshot to disk."""
    snap_dir = _snapshot_dir(project_root)
    snap_dir.mkdir(parents=True, exist_ok=True)

    filepath = snap_dir / f"{snapshot.snapshot_id}.yaml"
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(snapshot.to_dict(), f)

    # Also save a pointer to the latest snapshot
    latest_path = snap_dir / "latest.yaml"
    with open(latest_path, "w", encoding="utf-8") as f:
        yaml.dump({"latest": snapshot.snapshot_id}, f)

    return filepath


def load_latest_snapshot(project_root: Path) -> Snapshot | None:
    """Load the most recent snapshot, or None if no snapshots exist."""
    snap_dir = _snapshot_dir(project_root)
    latest_path = snap_dir / "latest.yaml"

    if not latest_path.exists():
        return None

    with open(latest_path, encoding="utf-8") as f:
        latest_data = yaml.load(f)

    if not latest_data or "latest" not in latest_data:
        return None

    snap_id = latest_data["latest"]
    snap_path = snap_dir / f"{snap_id}.yaml"

    if not snap_path.exists():
        return None

    with open(snap_path, encoding="utf-8") as f:
        data = yaml.load(f)

    return Snapshot.from_dict(data)


def load_snapshot(project_root: Path, snapshot_id: str) -> Snapshot | None:
    """Load a specific snapshot by ID."""
    snap_path = _snapshot_dir(project_root) / f"{snapshot_id}.yaml"
    if not snap_path.exists():
        return None

    with open(snap_path, encoding="utf-8") as f:
        data = yaml.load(f)

    return Snapshot.from_dict(data)

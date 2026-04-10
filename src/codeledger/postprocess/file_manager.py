"""File manager — handles doc naming, manifest tracking, and content hashing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

yaml = YAML()
yaml.default_flow_style = False

MANIFEST_FILE = ".codeledger/manifest.yaml"
DOCS_DIR = ".codeledger/docs"


@dataclass
class DocRecord:
    """Record of a single generated documentation file."""

    doc_id: str
    path: str
    timestamp: str
    session_type: str
    model: str
    files_analyzed: int
    content_hash: str


@dataclass
class Manifest:
    """Tracks all generated documentation files."""

    docs: list[DocRecord] = field(default_factory=list)
    last_doc_id: Optional[str] = None
    total_docs: int = 0
    merge_state: str = "pending"  # pending | complete | stale

    def next_doc_id(self) -> str:
        """Generate the next sequential doc ID."""
        self.total_docs += 1
        return f"pd_{self.total_docs:03d}"

    def add_doc(self, record: DocRecord) -> None:
        self.docs.append(record)
        self.last_doc_id = record.doc_id
        self.merge_state = "stale" if self.total_docs > 1 else "pending"

    def get_doc(self, doc_id: str) -> Optional[DocRecord]:
        for d in self.docs:
            if d.doc_id == doc_id:
                return d
        return None

    def doc_paths(self) -> list[str]:
        return [d.path for d in self.docs]

    def to_dict(self) -> dict:
        return {
            "docs": [
                {
                    "doc_id": d.doc_id,
                    "path": d.path,
                    "timestamp": d.timestamp,
                    "session_type": d.session_type,
                    "model": d.model,
                    "files_analyzed": d.files_analyzed,
                    "content_hash": d.content_hash,
                }
                for d in self.docs
            ],
            "last_doc_id": self.last_doc_id,
            "total_docs": self.total_docs,
            "merge_state": self.merge_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        docs = [
            DocRecord(
                doc_id=d["doc_id"],
                path=d["path"],
                timestamp=d["timestamp"],
                session_type=d.get("session_type", "standard"),
                model=d.get("model", "unknown"),
                files_analyzed=d.get("files_analyzed", 0),
                content_hash=d.get("content_hash", ""),
            )
            for d in data.get("docs", [])
        ]
        return cls(
            docs=docs,
            last_doc_id=data.get("last_doc_id"),
            total_docs=data.get("total_docs", len(docs)),
            merge_state=data.get("merge_state", "pending"),
        )


def content_hash(text: str) -> str:
    """Compute SHA-256 hash of document content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_manifest(project_root: Path) -> Manifest:
    """Load the doc manifest from disk."""
    manifest_path = project_root / MANIFEST_FILE
    if not manifest_path.exists():
        return Manifest()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    if not data:
        return Manifest()

    return Manifest.from_dict(data)


def save_manifest(project_root: Path, manifest: Manifest) -> None:
    """Save the doc manifest to disk."""
    manifest_path = project_root / MANIFEST_FILE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest.to_dict(), f)


def save_doc(
    project_root: Path,
    doc_id: str,
    content: str,
    session_type: str,
    model: str,
    files_analyzed: int,
    manifest: Manifest,
) -> Path:
    """Save a generated documentation file and update the manifest.

    Returns the path to the saved file.
    """
    docs_dir = project_root / DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{doc_id}.md"
    filepath = docs_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    record = DocRecord(
        doc_id=doc_id,
        path=str(filepath.relative_to(project_root)),
        timestamp=datetime.now(timezone.utc).isoformat(),
        session_type=session_type,
        model=model,
        files_analyzed=files_analyzed,
        content_hash=content_hash(content),
    )

    manifest.add_doc(record)
    save_manifest(project_root, manifest)

    return filepath


def load_all_docs(project_root: Path) -> list[tuple[str, str]]:
    """Load all generated doc files.

    Returns list of (doc_id, content) tuples in order.
    """
    manifest = load_manifest(project_root)
    docs = []

    for record in manifest.docs:
        filepath = project_root / record.path
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            docs.append((record.doc_id, content))

    return docs

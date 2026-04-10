"""Change DAG — Directed Acyclic Graph for change-aware documentation scoping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from codeledger.scanner.dependency import build_import_graph, build_reverse_graph
from codeledger.scanner.file_scanner import FileManifest
from codeledger.scanner.snapshot import ChangeType, FileChange, SnapshotDiff


@dataclass
class DAGNode:
    """A node in the Change DAG representing a file."""

    path: str
    change_type: str  # created | modified | deleted | unchanged | affected
    lines_before: int = 0
    lines_after: int = 0
    lines_delta: int = 0
    dependencies_in: set[str] = field(default_factory=set)   # files this imports
    dependencies_out: set[str] = field(default_factory=set)  # files that import this

    @property
    def is_changed(self) -> bool:
        return self.change_type in (ChangeType.CREATED, ChangeType.MODIFIED, ChangeType.DELETED)

    @property
    def is_affected(self) -> bool:
        return self.change_type == "affected"

    @property
    def change_magnitude(self) -> float:
        """0.0 to 1.0 score of how significant the change is based on line delta."""
        if self.change_type == ChangeType.CREATED:
            return min(1.0, self.lines_after / 200.0)
        if self.change_type == ChangeType.DELETED:
            return min(1.0, self.lines_before / 200.0)
        if self.change_type == ChangeType.MODIFIED:
            return min(1.0, abs(self.lines_delta) / 100.0)
        return 0.0


@dataclass
class ChangeSubgraph:
    """The extracted subgraph of changed + affected nodes."""

    changed_nodes: dict[str, DAGNode] = field(default_factory=dict)
    affected_nodes: dict[str, DAGNode] = field(default_factory=dict)

    @property
    def all_nodes(self) -> dict[str, DAGNode]:
        return {**self.changed_nodes, **self.affected_nodes}

    @property
    def all_paths(self) -> list[str]:
        return list(self.all_nodes.keys())

    @property
    def changed_paths(self) -> list[str]:
        return list(self.changed_nodes.keys())

    @property
    def affected_paths(self) -> list[str]:
        return list(self.affected_nodes.keys())

    @property
    def is_empty(self) -> bool:
        return len(self.changed_nodes) == 0

    def metrics(self) -> "ChangeMetrics":
        """Compute aggregate change metrics for session classification."""
        files_changed = len(self.changed_nodes)
        new_files = sum(
            1 for n in self.changed_nodes.values()
            if n.change_type == ChangeType.CREATED
        )
        files_deleted = sum(
            1 for n in self.changed_nodes.values()
            if n.change_type == ChangeType.DELETED
        )
        lines_added = sum(
            max(0, n.lines_delta) for n in self.changed_nodes.values()
            if n.change_type == ChangeType.MODIFIED
        ) + sum(
            n.lines_after for n in self.changed_nodes.values()
            if n.change_type == ChangeType.CREATED
        )
        lines_removed = sum(
            abs(min(0, n.lines_delta)) for n in self.changed_nodes.values()
            if n.change_type == ChangeType.MODIFIED
        ) + sum(
            n.lines_before for n in self.changed_nodes.values()
            if n.change_type == ChangeType.DELETED
        )
        affected_count = len(self.affected_nodes)

        total_magnitude = sum(n.change_magnitude for n in self.changed_nodes.values())

        return ChangeMetrics(
            files_changed=files_changed,
            new_files_created=new_files,
            files_deleted=files_deleted,
            lines_added=lines_added,
            lines_removed=lines_removed,
            net_lines=lines_added - lines_removed,
            affected_nodes_count=affected_count,
            total_magnitude=total_magnitude,
            has_structural_changes=new_files > 0 or files_deleted > 0,
        )


@dataclass
class ChangeMetrics:
    """Aggregate metrics about changes — input to the session classifier."""

    files_changed: int = 0
    new_files_created: int = 0
    files_deleted: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    net_lines: int = 0
    affected_nodes_count: int = 0
    total_magnitude: float = 0.0
    has_structural_changes: bool = False


class ProjectDAG:
    """Builds and queries the project dependency DAG."""

    def __init__(self) -> None:
        self.nodes: dict[str, DAGNode] = {}
        self._forward_graph: dict[str, set[str]] = {}
        self._reverse_graph: dict[str, set[str]] = {}

    def build(self, manifest: FileManifest, project_root: "Path") -> None:
        """Build the DAG from a file manifest."""
        from pathlib import Path as P

        # Build import graph
        self._forward_graph = build_import_graph(manifest, P(project_root))
        self._reverse_graph = build_reverse_graph(self._forward_graph)

        # Create nodes for all files
        for fi in manifest.files:
            self.nodes[fi.path] = DAGNode(
                path=fi.path,
                change_type=ChangeType.UNCHANGED,
                lines_after=fi.lines,
                lines_before=fi.lines,
                dependencies_in=self._forward_graph.get(fi.path, set()),
                dependencies_out=self._reverse_graph.get(fi.path, set()),
            )

    def mark_changes(self, diff: SnapshotDiff) -> set[str]:
        """Mark nodes as changed based on a snapshot diff.

        Returns the set of changed node paths.
        """
        changed: set[str] = set()

        for change in diff.changes:
            if change.path in self.nodes:
                node = self.nodes[change.path]
                node.change_type = change.change_type
                node.lines_before = change.lines_before
                node.lines_after = change.lines_after
                node.lines_delta = change.lines_delta
                changed.add(change.path)
            elif change.change_type == ChangeType.CREATED:
                # New file — create a node for it
                self.nodes[change.path] = DAGNode(
                    path=change.path,
                    change_type=ChangeType.CREATED,
                    lines_after=change.lines_after,
                    lines_delta=change.lines_after,
                )
                changed.add(change.path)

        return changed

    def propagate_effects(self, changed: set[str]) -> set[str]:
        """Propagate change effects up the reverse dependency graph.

        DFS traversal: for each changed file, find all files that depend on it.
        Returns the set of affected (but not directly changed) node paths.
        """
        affected: set[str] = set()
        visited: set[str] = set()

        def _dfs(path: str) -> None:
            if path in visited:
                return
            visited.add(path)

            dependents = self._reverse_graph.get(path, set())
            for dep in dependents:
                if dep not in changed:
                    affected.add(dep)
                    if dep in self.nodes:
                        self.nodes[dep].change_type = "affected"
                _dfs(dep)

        for path in changed:
            _dfs(path)

        return affected

    def extract_subgraph(self, diff: SnapshotDiff) -> ChangeSubgraph:
        """Extract the minimal subgraph of changed + affected nodes.

        This is the main entry point: mark changes, propagate, return subgraph.
        """
        changed_paths = self.mark_changes(diff)
        affected_paths = self.propagate_effects(changed_paths)

        subgraph = ChangeSubgraph()

        for path in changed_paths:
            if path in self.nodes:
                subgraph.changed_nodes[path] = self.nodes[path]

        for path in affected_paths:
            if path in self.nodes:
                subgraph.affected_nodes[path] = self.nodes[path]

        return subgraph

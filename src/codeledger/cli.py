"""CLI — Typer-based command-line interface for CodeLedger."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import codeledger
from codeledger.config.loader import (
    init_project,
    list_presets,
    load_config,
)

app = typer.Typer(
    name="codeledger",
    help="Auto-generated code comprehension for AI-assisted development.",
    no_args_is_help=True,
)
console = Console()


def _resolve_root(project_dir: Path | None) -> Path:
    """Resolve the project root directory."""
    if project_dir is None:
        return Path.cwd()
    return project_dir.resolve()


# ── init ──


@app.command()
def init(
    project_dir: Path | None = typer.Argument(
        None, help="Project root directory (defaults to current directory)."
    ),
    preset: str | None = typer.Option(None, "--preset", "-p", help="Configuration preset to use."),
    name: str | None = typer.Option(None, "--name", "-n", help="Project name."),
    language: str | None = typer.Option(
        None, "--lang", "-l", help="Primary language (python, javascript, etc.)."
    ),
    list_all_presets: bool = typer.Option(
        False, "--list-presets", help="List available presets and exit."
    ),
) -> None:
    """Initialize CodeLedger for a project."""
    if list_all_presets:
        presets = list_presets()
        console.print("[bold]Available presets:[/bold]")
        for p in presets:
            console.print(f"  - {p}")
        raise typer.Exit()

    root = _resolve_root(project_dir)

    try:
        config = init_project(
            project_root=root,
            preset=preset,
            project_name=name,
            language=language,
        )
        console.print(
            Panel(
                f"[green]Initialized CodeLedger[/green] for [bold]{config.project.name}[/bold]\n"
                f"Config: {root / '.codeledger' / 'config.yaml'}\n"
                f"Preset: {preset or 'default'}",
                title="codeledger init",
            )
        )
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e


# ── generate ──


@app.command()
def generate(
    project_dir: Path | None = typer.Argument(None, help="Project root directory."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force generation even if no changes detected."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be generated without calling the model."
    ),
) -> None:
    """Generate documentation based on current project state."""
    root = _resolve_root(project_dir)

    try:
        config = load_config(root)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    with console.status("[bold blue]Scanning project...[/bold blue]"):
        # 1. Scan files
        from codeledger.scanner import (
            ProjectDAG,
            compare_snapshots,
            create_snapshot,
            load_latest_snapshot,
            save_snapshot,
            scan_project,
        )

        manifest = scan_project(
            root,
            include_patterns=config.focus.include_patterns,
            exclude_patterns=config.focus.exclude_patterns,
        )
        console.print(
            f"  Scanned [bold]{manifest.total_files}[/bold] files ({manifest.total_lines} lines)"
        )

        # 2. Snapshot comparison
        old_snapshot = load_latest_snapshot(root)
        new_snapshot = create_snapshot(manifest)

        if old_snapshot:
            diff = compare_snapshots(old_snapshot, new_snapshot)
            if diff.is_empty and not force:
                console.print(
                    "[yellow]No changes detected.[/yellow] Use --force to generate anyway."
                )
                raise typer.Exit()
            console.print(
                f"  Changes: [green]+{diff.files_created}[/green] created, "
                f"[yellow]~{diff.files_modified}[/yellow] modified, "
                f"[red]-{diff.files_deleted}[/red] deleted"
            )
        else:
            diff = None
            console.print("  [dim]First scan — no previous snapshot[/dim]")

        # 3. Build Change DAG
        dag = ProjectDAG()
        dag.build(manifest, root)
        subgraph = dag.extract_subgraph(diff) if diff else None

    # 4. Classify session
    from codeledger.classifier import SessionType, classify_session

    if subgraph and not subgraph.is_empty:
        metrics = subgraph.metrics()
        classification = classify_session(metrics)
    else:
        # First run or forced — treat as STANDARD
        from codeledger.classifier.session import SessionClassification

        classification = SessionClassification(
            session_type=SessionType.STANDARD,
            confidence=1.0,
            input_token_budget=config.model.max_input_tokens,
            output_token_budget=config.model.max_output_tokens,
            reason="Initial scan or forced generation",
        )

    console.print(
        f"  Session: [bold]{classification.session_type.value}[/bold] "
        f"(confidence: {classification.confidence:.0%})"
    )

    # 5. Handle deferred sessions
    if classification.should_defer and not force:
        from codeledger.classifier.deferred import load_pending, save_pending

        pending = load_pending(root)
        if subgraph and not subgraph.is_empty:
            pending.add_session(
                changed_paths=diff.changed_paths() if diff else [],
                metrics=subgraph.metrics(),
                summary=f"Deferred: {classification.session_type.value}",
            )
        save_pending(root, pending)
        console.print("[dim]Trivial changes deferred. Use --force to generate anyway.[/dim]")
        # Save snapshot even though we deferred
        save_snapshot(root, new_snapshot)
        raise typer.Exit()

    if dry_run:
        console.print(
            Panel(
                f"Session type: {classification.session_type.value}\n"
                f"Input budget: {classification.input_token_budget} tokens\n"
                f"Output budget: {classification.output_token_budget} tokens\n"
                f"Files to analyze: {manifest.total_files}\n"
                f"Model: {config.model.model_name}",
                title="Dry Run",
            )
        )
        raise typer.Exit()

    # 6. Parse and compress
    with console.status("[bold blue]Analyzing code...[/bold blue]"):
        from codeledger.compressor import compress_project, trim_to_budget
        from codeledger.parser import parse_file

        parsed_files = []
        for fi in manifest.code_files():
            try:
                parsed = parse_file(fi.absolute_path, fi.language or "")
                parsed_files.append(parsed)
            except Exception:
                pass  # Skip unparseable files

        compressed = compress_project(parsed_files)
        trimmed_files, trimmed_sections = trim_to_budget(
            compressed,
            config.template_sections,
            classification.input_token_budget,
        )

    # 7. Build prompt and generate
    from codeledger.generator import build_generation_prompt
    from codeledger.generator import generate as gen_call

    system_prompt, user_prompt = build_generation_prompt(
        compressed_payload=trimmed_files,
        sections=trimmed_sections,
        session_type=classification.session_type,
        project_name=config.project.name,
        focus_highlights=config.focus.highlight or None,
    )

    with console.status(f"[bold blue]Generating with {config.model.model_name}...[/bold blue]"):
        response = gen_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config.model,
        )

    console.print(
        f"  Generated {response.output_tokens} tokens in {response.latency_ms / 1000:.1f}s"
    )

    # 8. Validate
    from codeledger.postprocess import validate_output

    known_paths = {fi.path for fi in manifest.files}
    section_names = [s.name for s in config.template_sections]
    validation = validate_output(response.content, section_names, known_paths)

    if validation.has_warnings:
        for w in validation.warnings:
            icon = "[red]✗[/red]" if w.severity == "error" else "[yellow]![/yellow]"
            console.print(f"  {icon} {w.message}")

    # 9. Format and save
    from codeledger.postprocess import format_doc, load_manifest, save_doc

    doc_manifest = load_manifest(root)
    doc_id = doc_manifest.next_doc_id()

    formatted = format_doc(
        content=response.content,
        doc_id=doc_id,
        project_name=config.project.name,
        model_name=config.model.model_name,
        session_type=classification.session_type.value,
        files_analyzed=len(parsed_files),
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )

    doc_path = save_doc(
        project_root=root,
        doc_id=doc_id,
        content=formatted,
        session_type=classification.session_type.value,
        model=config.model.model_name,
        files_analyzed=len(parsed_files),
        manifest=doc_manifest,
    )

    # 10. Save new snapshot
    new_snapshot.doc_id = doc_id
    save_snapshot(root, new_snapshot)

    console.print(
        Panel(
            f"[green]Documentation generated:[/green] {doc_path.relative_to(root)}\n"
            f"Doc ID: [bold]{doc_id}[/bold]",
            title="codeledger generate",
        )
    )


# ── merge ──


@app.command()
def merge(
    project_dir: Path | None = typer.Argument(None, help="Project root directory."),
    local_only: bool = typer.Option(False, "--local", help="Merge locally without calling an LLM."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path for merged doc."
    ),
) -> None:
    """Merge all generated docs into a single conceptualized document."""
    root = _resolve_root(project_dir)

    try:
        config = load_config(root)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    from codeledger.merge import merge_local as ml
    from codeledger.merge import merge_with_llm

    with console.status("[bold blue]Merging documentation...[/bold blue]"):
        content = ml(root) if local_only else merge_with_llm(root, config)

    # Write output
    out_path = output.resolve() if output else root / ".codeledger" / "DOCUMENTATION.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    console.print(
        Panel(
            f"[green]Merged documentation written to:[/green] {out_path}",
            title="codeledger merge",
        )
    )


# ── status ──


@app.command()
def status(
    project_dir: Path | None = typer.Argument(None, help="Project root directory."),
) -> None:
    """Show the current CodeLedger status for a project."""
    root = _resolve_root(project_dir)

    try:
        config = load_config(root)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    from codeledger.postprocess.file_manager import load_manifest

    manifest = load_manifest(root)

    table = Table(title=f"CodeLedger Status — {config.project.name}")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Project", config.project.name)
    table.add_row("Language", config.project.language)
    table.add_row("Model", config.model.model_name)
    table.add_row("Docs generated", str(manifest.total_docs))
    table.add_row("Last doc ID", manifest.last_doc_id or "—")
    table.add_row("Merge state", manifest.merge_state)
    table.add_row("Cadence (N)", str(config.cadence.n_value))
    table.add_row("Trigger", config.cadence.trigger.value)

    console.print(table)

    if manifest.docs:
        doc_table = Table(title="Generated Documents")
        doc_table.add_column("ID", style="cyan")
        doc_table.add_column("Session")
        doc_table.add_column("Model")
        doc_table.add_column("Files")
        doc_table.add_column("Timestamp")

        for doc in manifest.docs:
            doc_table.add_row(
                doc.doc_id,
                doc.session_type,
                doc.model,
                str(doc.files_analyzed),
                doc.timestamp[:19],
            )
        console.print(doc_table)


# ── diff ──


@app.command()
def diff(
    project_dir: Path | None = typer.Argument(None, help="Project root directory."),
) -> None:
    """Show changes since the last snapshot."""
    root = _resolve_root(project_dir)

    try:
        config = load_config(root)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e

    from codeledger.scanner import (
        compare_snapshots,
        create_snapshot,
        load_latest_snapshot,
        scan_project,
    )

    manifest = scan_project(
        root,
        include_patterns=config.focus.include_patterns,
        exclude_patterns=config.focus.exclude_patterns,
    )
    old_snapshot = load_latest_snapshot(root)

    if not old_snapshot:
        console.print(
            "[yellow]No previous snapshot found.[/yellow] Run 'codeledger generate' first."
        )
        raise typer.Exit()

    new_snapshot = create_snapshot(manifest)
    snap_diff = compare_snapshots(old_snapshot, new_snapshot)

    if snap_diff.is_empty:
        console.print("[green]No changes detected since last snapshot.[/green]")
        raise typer.Exit()

    table = Table(title="Changes Since Last Snapshot")
    table.add_column("Status", width=10)
    table.add_column("File")
    table.add_column("Lines Δ", justify="right")

    for change in snap_diff.changes:
        if change.change_type == "created":
            status_str = "[green]+ created[/green]"
        elif change.change_type == "modified":
            status_str = "[yellow]~ modified[/yellow]"
        else:
            status_str = "[red]- deleted[/red]"

        delta = change.lines_delta
        delta_str = f"+{delta}" if delta > 0 else str(delta)

        table.add_row(status_str, change.path, delta_str)

    console.print(table)
    console.print(
        f"\nTotal: [green]+{snap_diff.files_created}[/green] "
        f"[yellow]~{snap_diff.files_modified}[/yellow] "
        f"[red]-{snap_diff.files_deleted}[/red]"
    )


# ── version ──


@app.command()
def version() -> None:
    """Show the CodeLedger version."""
    console.print(f"codeledger {codeledger.__version__}")


# ── explain ──


@app.command()
def explain(
    doc_id: str = typer.Argument(..., help="Document ID to explain (e.g., pd_001)."),
    project_dir: Path | None = typer.Option(
        None, "--project", "-p", help="Project root directory."
    ),
) -> None:
    """Display a generated document by its ID."""
    root = _resolve_root(project_dir)

    from codeledger.postprocess.file_manager import load_manifest

    manifest = load_manifest(root)
    record = manifest.get_doc(doc_id)

    if not record:
        console.print(f"[red]Error:[/red] Document '{doc_id}' not found.")
        raise typer.Exit(code=1)

    doc_path = root / record.path
    if not doc_path.exists():
        console.print(f"[red]Error:[/red] Document file missing: {record.path}")
        raise typer.Exit(code=1)

    content = doc_path.read_text(encoding="utf-8")
    from rich.markdown import Markdown

    console.print(Markdown(content))

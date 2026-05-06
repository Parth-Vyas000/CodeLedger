# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-05-06

### Fixed

- `SIM103`: Simplified redundant if/return/return pattern in `DeferredSessionAccumulator.should_flush`
- `B904`: Added `raise ... from e` chaining to all `except` clauses in CLI commands (`init`, `generate`, `merge`, `status`, `diff`)
- `SIM108`: Converted if/else blocks to ternary operators in `cli.py` and `config/loader.py`
- `B007`: Renamed unused loop variable `key` to `_key` in `merge/deduplicator.py`
- `SIM101`: Merged two `isinstance` calls into one union check in `parser/python_parser.py`
- `F821`/`N817`: Moved `from pathlib import Path` to module level in `scanner/change_dag.py`, removing the local `import Path as P` antipattern
- `SIM102`: Combined nested `if` statements in `compressor/token_compressor.py` and `scanner/dependency.py`
- `RUF059`: Prefixed unused unpacked variables with `_` in test files
- Added `[tool.ruff.lint.per-file-ignores]` to suppress `B008` for `cli.py` (Typer requires function-call defaults by design)

## [0.1.0] - 2025-06-29

### Added

- Initial release
- CLI commands: `init`, `generate`, `merge`, `status`, `diff`, `explain`, `version`
- File scanner with gitignore-aware traversal
- Snapshot engine for hash-based change detection (no git required)
- Dependency resolver and Change DAG for propagation-aware scoping
- Python AST parser with complexity estimation
- Regex-based fallback parser for JS/TS, Java, Go, Rust
- Rule-based session classifier (trivial/minor/standard/major/refactor)
- Deferred session accumulator for batching trivial changes
- Token compressor with scope engine for budget-aware payload trimming
- Prompt builder with 4 template tiers (micro, standard, refactor, merge)
- Model router supporting Anthropic, OpenAI, and Ollama backends
- Output validator with hallucination detection and section checking
- Jinja2-based markdown formatter with metadata injection
- File manager with manifest tracking and content hashing
- Merge engine with local deduplication and LLM-powered conceptualization
- 7 configuration presets (python_api, react_frontend, fullstack, data_pipeline, ml_research, cli_tool, minimal)

<div align="center">

# 📄 CodeLedger

**Auto-generated code comprehension for AI-assisted development**


[![PyPI](https://img.shields.io/pypi/v/codeledger)](https://pypi.org/project/codeledger/)
[![Python](https://img.shields.io/pypi/pyversions/codeledger)](https://pypi.org/project/codeledger/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*Documentation as a development cadence — not an afterthought.*

</div>

---

## Why CodeLedger?

AI-assisted ("vibe") coding moves fast. Code evolves through rapid iteration with LLMs, and traditional documentation can't keep up. Six months later, you (or a new team member) opens the project and has no idea *why* anything was built the way it was.

**CodeLedger** generates structured documentation at configurable intervals during development — capturing architecture decisions, component logic, and integration patterns *while your project evolves*, not after.

### Who is this for?

- **Solo devs** who vibe-code with AI and want to remember what they built
- **Teams** onboarding new members to AI-iterated codebases
- **Anyone** tired of writing docs after the fact (so... everyone?)

## How It Works

```
Your Code → Scan → Parse → Classify → Compress → Generate → Doc
                                                     ↓
                              Multiple Docs → Merge → Final Documentation
```

1. **Scan** — Walks your project, respects `.gitignore`, builds a file manifest
2. **Snapshot** — Hash-based change detection (no git required)
3. **Parse** — AST analysis (Python) or regex extraction (JS/TS, Java, Go, Rust)
4. **Classify** — Determines session scope: trivial → minor → standard → major → refactor
5. **Compress** — Token-efficient representation within your model's budget
6. **Generate** — Sends structured prompt to Anthropic, OpenAI, or Ollama
7. **Merge** — Combines multiple doc snapshots into a single conceptualized document

## Quick Start

### Install

```bash
pip install codeledger
```

### Initialize

```bash
cd your-project
codeledger init --preset python_api
```

This creates `.codeledger/config.yaml` with sensible defaults for your project type.

### Generate Documentation

```bash
codeledger generate
```

CodeLedger scans your code, detects what changed, classifies the session, and generates a structured doc snapshot.

### Merge Into Final Docs

```bash
codeledger merge
```

Combines all generated snapshots into a single `DOCUMENTATION.md`.

### Other Commands

```bash
codeledger status       # Show project status and doc history
codeledger diff         # Show changes since last snapshot
codeledger explain pd_001  # Display a specific doc by ID
codeledger version      # Show version
```

## Configuration

After `codeledger init`, edit `.codeledger/config.yaml`:

```yaml
project:
  name: my-project
  language: python
  type: api

cadence:
  n_value: 5          # Generate every N interactions
  trigger: manual     # manual | file_watch | time_interval

model:
  tier: api
  provider: anthropic
  model_name: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
  max_input_tokens: 3000
  max_output_tokens: 5000

focus:
  include_patterns:
    - "**/*.py"
  exclude_patterns:
    - "tests/**"
    - "__pycache__/**"
  highlight:
    - "src/core/engine.py"   # Pay extra attention to these files
```

### Presets

Start fast with a preset that matches your project:

| Preset | Use Case |
|--------|----------|
| `python_api` | Python REST/GraphQL APIs |
| `react_frontend` | React/Next.js frontends |
| `fullstack` | Full-stack applications |
| `data_pipeline` | ETL and data processing |
| `ml_research` | ML/AI research projects |
| `cli_tool` | Command-line tools |
| `minimal` | Bare minimum setup |

```bash
codeledger init --preset fullstack --name my-app
```

## Model Support

| Provider | Tier | Setup |
|----------|------|-------|
| **Anthropic** | Cloud | Set `ANTHROPIC_API_KEY` env var |
| **OpenAI** | Cloud | Set `OPENAI_API_KEY` env var |
| **Ollama** | Local (free) | Install [Ollama](https://ollama.ai), pull a model |

### Using Ollama (free, runs locally)

```yaml
model:
  tier: local
  provider: ollama
  model_name: llama3.1
  max_output_tokens: 5000
```

No API key needed — runs entirely on your machine.

## Smart Session Classification

CodeLedger doesn't waste tokens on tiny changes. It classifies each session to calibrate documentation depth:

| Type | When | Token Budget | What Happens |
|------|------|-------------|--------------|
| **Trivial** | <2 files, <30 lines | 0 | Deferred and batched |
| **Minor** | <5 files, <150 lines | ~1.5K | Micro-doc generated |
| **Standard** | <15 files, <500 lines | ~5K | Full documentation |
| **Major** | 15+ files, 500+ lines | ~8K | Comprehensive deep-dive |
| **Refactor** | Many deletes + creates | ~3K | Refactor-focused analysis |

Trivial sessions are automatically deferred and batched until they accumulate enough significance — so you only pay for docs when they matter.

## No Git Required

CodeLedger uses its own **Snapshot Engine** — SHA-256 hashing of file contents for change detection. Git is completely optional.

This means it works for:

- Projects without version control
- Quick prototypes and experiments
- Environments where git isn't available
- Vibe coding sessions where you just want to build

## What Gets Documented

Each generated doc includes up to 9 configurable sections:

| Section | What It Captures |
|---------|-----------------|
| **Phase Execution Summary** | What was built and current status |
| **Code Architecture** | File tree and structural overview |
| **Decision Rationale** | Why things were built this way |
| **Component Logic** | How non-obvious parts work |
| **Integration & Data Flow** | How components connect |
| **Edge Cases & Error Handling** | Boundary conditions and failure modes |
| **Interview & Learning Notes** | Q&A format insights |
| **Technical Debt** | Known issues and future work |
| **Quick Reference** | Common commands and entry points |

Sections are prioritized (P1/P2/P3) and automatically trimmed to fit your token budget.

## Architecture

```
src/codeledger/
├── config/          # Pydantic schema, YAML loader, 7 presets
├── scanner/         # File scanner, snapshot engine, dependency resolver, Change DAG
├── parser/          # Python AST parser + regex fallback for JS/TS, Java, Go, Rust
├── classifier/      # Rule-based session classification with deferred batching
├── compressor/      # Token compression and budget-aware scope trimming
├── generator/       # Prompt builder, model router, API + local clients
├── postprocess/     # Output validation, formatting, file management
├── merge/           # Multi-doc extraction, deduplication, merge engine
├── templates/       # 4 prompt templates + 2 Jinja2 output templates
└── cli.py           # Typer CLI entry point
```

**Key design decisions:**
- **No git dependency** — Snapshot engine uses SHA-256 hashing
- **Change DAG** — Dependency graph propagation for token-efficient scoping
- **Budget-aware pipeline** — Every stage respects the configured token limit
- **Validation layer** — Catches hallucinated file paths, checks section coverage

## Development

```bash
git clone https://github.com/codeledger/codeledger.git
cd codeledger
pip install -e ".[dev]"

pytest                          # Run tests
ruff check src/ tests/          # Lint
ruff format src/ tests/         # Format
mypy src/codeledger/             # Type check
```

## Roadmap

- [x] Core pipeline (scan → parse → classify → compress → generate)
- [x] Snapshot engine (git-free change detection)
- [x] Change DAG with dependency propagation
- [x] Session classifier with deferred batching
- [x] Multi-model support (Anthropic, OpenAI, Ollama)
- [x] Merge engine with deduplication
- [ ] File watcher mode for automatic triggers
- [ ] Tree-sitter parsers for deeper JS/TS and Java analysis
- [ ] MkDocs documentation site
- [ ] VS Code extension

## License

[MIT](LICENSE) — Use it however you want.

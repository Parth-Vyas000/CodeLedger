"""Configuration loader — reads, validates, and writes .codeledger/config.yaml."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from codeledger.config.schema import CodeLedgerConfig

CODELEDGER_DIR = ".codeledger"
CONFIG_FILE = "config.yaml"
DOCS_DIR = "docs"
CACHE_DIR = ".cache"

yaml = YAML()
yaml.default_flow_style = False
yaml.preserve_quotes = True


def get_codeledger_dir(project_root: Path) -> Path:
    """Return the .codeledger directory path for a project."""
    return project_root / CODELEDGER_DIR


def get_config_path(project_root: Path) -> Path:
    """Return the config.yaml path for a project."""
    return get_codeledger_dir(project_root) / CONFIG_FILE


def ensure_codeledger_structure(project_root: Path) -> Path:
    """Create the .codeledger directory structure if it doesn't exist.

    Returns the .codeledger directory path.
    """
    pd_dir = get_codeledger_dir(project_root)
    (pd_dir / DOCS_DIR).mkdir(parents=True, exist_ok=True)
    (pd_dir / CACHE_DIR).mkdir(parents=True, exist_ok=True)
    return pd_dir


def load_config(project_root: Path) -> CodeLedgerConfig:
    """Load and validate the configuration from .codeledger/config.yaml.

    Raises FileNotFoundError if the config file doesn't exist.
    """
    config_path = get_config_path(project_root)
    if not config_path.exists():
        raise FileNotFoundError(
            f"No CodeLedger config found at {config_path}. Run 'codeledger init' first."
        )

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.load(f)

    if raw is None:
        raw = {}

    return CodeLedgerConfig.model_validate(raw)


def save_config(project_root: Path, config: CodeLedgerConfig) -> Path:
    """Save configuration to .codeledger/config.yaml.

    Returns the path to the saved config file.
    """
    pd_dir = ensure_codeledger_structure(project_root)
    config_path = pd_dir / CONFIG_FILE

    data = config.model_dump(mode="json")

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return config_path


def load_preset(preset_name: str) -> CodeLedgerConfig:
    """Load a preset configuration by name.

    Available presets: python_api, react_frontend, fullstack,
    data_pipeline, ml_research, cli_tool, minimal.
    """
    presets_dir = Path(__file__).parent / "presets"
    preset_path = presets_dir / f"{preset_name}.yaml"

    if not preset_path.exists():
        available = [p.stem for p in presets_dir.glob("*.yaml")]
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {', '.join(sorted(available))}"
        )

    with open(preset_path, encoding="utf-8") as f:
        raw = yaml.load(f)

    if raw is None:
        raw = {}

    return CodeLedgerConfig.model_validate(raw)


def list_presets() -> list[str]:
    """Return a list of available preset names."""
    presets_dir = Path(__file__).parent / "presets"
    return sorted(p.stem for p in presets_dir.glob("*.yaml"))


def init_project(
    project_root: Path,
    preset: str | None = None,
    project_name: str | None = None,
    language: str | None = None,
) -> CodeLedgerConfig:
    """Initialize a new CodeLedger project.

    Creates .codeledger/ directory structure and config.yaml.
    Returns the created configuration.
    """
    config_path = get_config_path(project_root)
    if config_path.exists():
        raise FileExistsError(
            f"CodeLedger already initialized at {config_path}. Delete .codeledger/ to reinitialize."
        )

    config = load_preset(preset) if preset else CodeLedgerConfig()

    if project_name:
        config.project.name = project_name
    elif project_name is None:
        config.project.name = project_root.name

    if language:
        config.project.language = language

    save_config(project_root, config)
    return config

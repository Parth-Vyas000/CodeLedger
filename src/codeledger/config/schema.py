"""Configuration schema — Pydantic models for .codeledger/config.yaml."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    WEB_APP = "web_app"
    API = "api"
    CLI = "cli"
    LIBRARY = "library"
    RESEARCH = "research"
    MOBILE = "mobile"
    FULLSTACK = "fullstack"
    DATA_PIPELINE = "data_pipeline"


class PhaseStyle(str, Enum):
    PHASED = "phased"
    CONTINUOUS = "continuous"


class TriggerMode(str, Enum):
    MANUAL = "manual"
    FILE_WATCH = "file_watch"
    TIME_INTERVAL = "time_interval"
    COMMIT_COUNT = "commit_count"


class ModelTier(str, Enum):
    API = "api"
    LOCAL = "local"


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    YAML_GRAPH = "yaml_graph"
    HYBRID = "hybrid"


class CompressionLevel(str, Enum):
    VERBOSE = "verbose"
    BALANCED = "balanced"
    MINIMAL = "minimal"


class SectionFormat(str, Enum):
    TABLE = "table"
    PROSE = "prose"
    YAML = "yaml"
    TREE_AND_YAML = "tree_and_yaml"
    ASCII_DIAGRAM = "ascii_diagram"
    QA = "qa"
    CODE_BLOCKS = "code_blocks"


class DepthLevel(str, Enum):
    ALL = "all"
    NON_OBVIOUS_ONLY = "non_obvious_only"
    COMPLEX_ONLY = "complex_only"


# ── Sub-models ──


class ProjectConfig(BaseModel):
    name: str = "my-project"
    language: str = "python"
    type: ProjectType = ProjectType.API
    phase_style: PhaseStyle = PhaseStyle.CONTINUOUS


class CadenceConfig(BaseModel):
    n_value: int = Field(default=5, ge=1, le=50)
    trigger: TriggerMode = TriggerMode.MANUAL
    commit_threshold: int = Field(default=5, ge=1)
    time_interval_minutes: int = Field(default=30, ge=5)


class ModelConfig(BaseModel):
    tier: ModelTier = ModelTier.API
    provider: ModelProvider = ModelProvider.ANTHROPIC
    model_name: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_input_tokens: int = Field(default=3000, ge=500)
    max_output_tokens: int = Field(default=5000, ge=1000)


class TemplateSectionConfig(BaseModel):
    id: str
    name: str
    priority: int = Field(default=2, ge=1, le=3)
    format: SectionFormat = SectionFormat.PROSE
    depth: DepthLevel | None = None


class FocusConfig(BaseModel):
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "tests/**",
            "*.lock",
            "node_modules/**",
            "__pycache__/**",
            ".git/**",
            ".codeledger/**",
            "*.pyc",
            ".venv/**",
            "venv/**",
        ]
    )
    highlight: list[str] = Field(default_factory=list)
    skip_trivial: bool = True


class OutputConfig(BaseModel):
    format: OutputFormat = OutputFormat.MARKDOWN
    compression: CompressionLevel = CompressionLevel.BALANCED
    include_line_numbers: bool = True
    include_ascii_diagrams: bool = True
    max_doc_tokens: int = Field(default=8000, ge=1000)


class ClassifierConfig(BaseModel):
    """Thresholds for the rule-based session classifier."""

    trivial_max_files: int = 2
    trivial_max_lines: int = 30
    minor_max_files: int = 5
    minor_max_lines: int = 150
    standard_max_files: int = 15
    standard_max_lines: int = 500
    max_deferred_sessions: int = 5
    flush_threshold: float = Field(default=0.40, ge=0.0, le=1.0)


# ── Root config ──

DEFAULT_SECTIONS: list[TemplateSectionConfig] = [
    TemplateSectionConfig(
        id="status", name="Phase Execution Summary", priority=1, format=SectionFormat.TABLE
    ),
    TemplateSectionConfig(
        id="architecture",
        name="Code Architecture",
        priority=1,
        format=SectionFormat.TREE_AND_YAML,
    ),
    TemplateSectionConfig(
        id="decisions", name="Decision Rationale", priority=1, format=SectionFormat.TABLE
    ),
    TemplateSectionConfig(
        id="logic",
        name="Component Logic",
        priority=2,
        format=SectionFormat.PROSE,
        depth=DepthLevel.NON_OBVIOUS_ONLY,
    ),
    TemplateSectionConfig(
        id="data_flow",
        name="Integration & Data Flow",
        priority=2,
        format=SectionFormat.ASCII_DIAGRAM,
    ),
    TemplateSectionConfig(
        id="edge_cases",
        name="Edge Cases & Error Handling",
        priority=2,
        format=SectionFormat.TABLE,
    ),
    TemplateSectionConfig(
        id="interview",
        name="Interview & Learning Notes",
        priority=3,
        format=SectionFormat.QA,
    ),
    TemplateSectionConfig(id="debt", name="Technical Debt", priority=3, format=SectionFormat.TABLE),
    TemplateSectionConfig(
        id="commands",
        name="Quick Reference",
        priority=1,
        format=SectionFormat.CODE_BLOCKS,
    ),
]


class CodeLedgerConfig(BaseModel):
    """Root configuration model for .codeledger/config.yaml."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    cadence: CadenceConfig = Field(default_factory=CadenceConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    template_sections: list[TemplateSectionConfig] = Field(
        default_factory=lambda: list(DEFAULT_SECTIONS)
    )
    focus: FocusConfig = Field(default_factory=FocusConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)

"""Generator package — prompt building and model routing."""

from codeledger.generator.api_client import ModelResponse
from codeledger.generator.model_router import generate
from codeledger.generator.prompt_builder import (
    build_generation_prompt,
    build_merge_prompt,
)

__all__ = [
    "ModelResponse",
    "build_generation_prompt",
    "build_merge_prompt",
    "generate",
]

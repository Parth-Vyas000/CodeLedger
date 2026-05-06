"""Compressor package — token compression and scope management."""

from codeledger.compressor.scope_engine import trim_to_budget
from codeledger.compressor.token_compressor import (
    compress_file,
    compress_project,
    estimate_tokens,
)

__all__ = [
    "compress_file",
    "compress_project",
    "estimate_tokens",
    "trim_to_budget",
]

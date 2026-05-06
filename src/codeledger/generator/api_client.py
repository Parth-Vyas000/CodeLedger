"""API client — handles communication with cloud LLM providers."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class ModelResponse:
    """Response from a model invocation."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    latency_ms: float


def call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "claude-sonnet-4-20250514",
    max_output_tokens: int = 5000,
    api_key_env: str = "ANTHROPIC_API_KEY",
) -> ModelResponse:
    """Call the Anthropic API."""
    import anthropic

    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise OSError(f"API key not found. Set the {api_key_env} environment variable.")

    client = anthropic.Anthropic(api_key=api_key)

    start = time.monotonic()
    response = client.messages.create(
        model=model_name,
        max_tokens=max_output_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = (time.monotonic() - start) * 1000

    content = ""
    for block in response.content:
        if hasattr(block, "text"):
            content += block.text

    return ModelResponse(
        content=content,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        finish_reason=response.stop_reason or "unknown",
        latency_ms=elapsed,
    )


def call_openai(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "gpt-4o-mini",
    max_output_tokens: int = 5000,
    api_key_env: str = "OPENAI_API_KEY",
) -> ModelResponse:
    """Call the OpenAI API."""
    import openai

    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise OSError(f"API key not found. Set the {api_key_env} environment variable.")

    client = openai.OpenAI(api_key=api_key)

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model_name,
        max_tokens=max_output_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    elapsed = (time.monotonic() - start) * 1000

    choice = response.choices[0]
    usage = response.usage

    return ModelResponse(
        content=choice.message.content or "",
        model=response.model or model_name,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        finish_reason=choice.finish_reason or "unknown",
        latency_ms=elapsed,
    )

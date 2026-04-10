"""Local client — handles communication with local model servers (Ollama, llama.cpp)."""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from codeledger.generator.api_client import ModelResponse


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "qwen2.5-coder:7b",
    max_output_tokens: int = 5000,
    base_url: str = "http://127.0.0.1:11434",
) -> ModelResponse:
    """Call a local Ollama server.

    Requires Ollama to be running locally with the specified model pulled.
    """
    url = f"{base_url}/api/chat"

    payload = json.dumps({
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "num_predict": max_output_tokens,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.monotonic()

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Cannot connect to Ollama at {base_url}. "
            f"Make sure Ollama is running: ollama serve"
        ) from e

    elapsed = (time.monotonic() - start) * 1000

    content = data.get("message", {}).get("content", "")

    # Ollama provides eval_count and prompt_eval_count
    input_tokens = data.get("prompt_eval_count", 0)
    output_tokens = data.get("eval_count", 0)

    return ModelResponse(
        content=content,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        finish_reason="stop",
        latency_ms=elapsed,
    )

"""Model router — routes generation requests to the appropriate model backend."""

from __future__ import annotations

from codeledger.config.schema import ModelConfig, ModelProvider, ModelTier
from codeledger.generator.api_client import ModelResponse


def generate(
    system_prompt: str,
    user_prompt: str,
    config: ModelConfig,
) -> ModelResponse:
    """Route a generation request to the configured model backend.

    Args:
        system_prompt: System/instruction prompt.
        user_prompt: User prompt with project context.
        config: Model configuration from config.yaml.

    Returns:
        ModelResponse with the generated content.
    """
    if config.tier == ModelTier.API:
        if config.provider == ModelProvider.ANTHROPIC:
            from codeledger.generator.api_client import call_anthropic
            return call_anthropic(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name=config.model_name,
                max_output_tokens=config.max_output_tokens,
                api_key_env=config.api_key_env,
            )
        elif config.provider == ModelProvider.OPENAI:
            from codeledger.generator.api_client import call_openai
            return call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name=config.model_name,
                max_output_tokens=config.max_output_tokens,
                api_key_env=config.api_key_env,
            )
        else:
            raise ValueError(f"Unsupported API provider: {config.provider}")

    elif config.tier == ModelTier.LOCAL:
        if config.provider == ModelProvider.OLLAMA:
            from codeledger.generator.local_client import call_ollama
            return call_ollama(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name=config.model_name,
                max_output_tokens=config.max_output_tokens,
            )
        else:
            raise ValueError(
                f"Unsupported local provider: {config.provider}. "
                f"Use 'ollama' for local inference."
            )

    raise ValueError(f"Unknown model tier: {config.tier}")

"""Provider-independent model backends for EthioContextEval."""

from __future__ import annotations

from ethiocontexteval.providers.base import (
    GenerationResult,
    ModelInfo,
    ModelProvider,
    ProviderError,
    get_provider,
)

__all__ = [
    "GenerationResult",
    "ModelInfo",
    "ModelProvider",
    "ProviderError",
    "get_provider",
]

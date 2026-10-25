"""Provider-independent model backends for MADAALA."""

from __future__ import annotations

from madaala.providers.base import (
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

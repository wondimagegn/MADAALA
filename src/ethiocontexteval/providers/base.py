"""Common provider abstraction and normalized generation results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


class ProviderError(RuntimeError):
    """Raised for hard provider failures (auth, missing deps, unavailable model)."""


@dataclass
class ModelInfo:
    """Normalized model catalog entry."""

    model_id: str
    name: str | None = None
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationResult:
    """Normalized single-generation outcome (ok or soft error)."""

    response: str | None
    model_id: str
    provider: str
    latency_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "ok"  # ok | error
    error: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelProvider(ABC):
    """Abstract model backend."""

    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]: ...

    @abstractmethod
    def generate(
        self,
        *,
        model_id: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.0,
        system: str | None = None,
    ) -> GenerationResult:
        """Run one generation. Soft failures return status='error' on the result."""

    def is_model_available(self, model_id: str) -> bool:
        """Discovery only; this does not establish runtime quota."""
        return model_id in {m.model_id for m in self.list_models()}

    def ensure_model_available(self, model_id: str) -> None:
        """Raise ProviderError if model_id is not available."""
        ids = {m.model_id for m in self.list_models()}
        if model_id in ids:
            return
        sample = ", ".join(sorted(ids)[:12]) if ids else "(none)"
        raise ProviderError(
            f"Model '{model_id}' not available for provider '{self.provider_name()}'. "
            f"Sample available: {sample}"
        )


def get_provider(
    name: str,
    *,
    region: str | None = None,
    profile: str | None = None,
    **kwargs: Any,
) -> ModelProvider:
    """Factory for provider backends. Supported: mock, bedrock."""
    key = (name or "bedrock").strip().lower()
    if key == "mock":
        from ethiocontexteval.providers.mock_provider import MockProvider

        return MockProvider(**kwargs)
    if key == "bedrock":
        from ethiocontexteval.providers.bedrock_provider import BedrockProvider

        return BedrockProvider(region_name=region, profile_name=profile, **kwargs)
    if key == "ollama":
        raise ProviderError(
            "Provider 'ollama' has been removed. Use 'bedrock' (or 'mock' for offline tests)."
        )
    raise ProviderError(f"Unknown provider '{name}'. Supported: mock, bedrock.")

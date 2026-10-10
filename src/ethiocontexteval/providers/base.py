"""Common provider abstraction and normalized generation results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


class ProviderError(RuntimeError):
    """Raised for configuration or hard provider failures (not per-prompt errors)."""


@dataclass
class ModelInfo:
    """Normalized model listing entry."""

    model_id: str
    name: str | None = None
    provider: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "provider": self.provider,
            "metadata": dict(self.metadata),
        }


@dataclass
class GenerationResult:
    """
    Provider-normalized generation outcome.

    Token counts and finish reasons are null when the backend does not supply them.
    Never invent metrics.
    """

    provider: str
    model_id: str
    response: str | None
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    status: str = "ok"  # ok | error
    error: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


class ModelProvider(ABC):
    """Abstract backend for text generation (Ollama, Bedrock, Mock, ...)."""

    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider id, e.g. 'ollama', 'bedrock', 'mock'."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Return a dict with at least {"ok": bool, "message": str}.
        Must not require paid cloud calls when using local/mock providers.
        """

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """List models visible to this provider (installed / accessible)."""

    @abstractmethod
    def generate(
        self,
        model_id: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> GenerationResult:
        """Run one generation. Soft failures return status='error' on the result."""

    def ensure_model_available(self, model_id: str) -> None:
        """Raise ProviderError if model_id is not among list_models()."""
        models = self.list_models()
        ids = {m.model_id for m in models}
        if model_id in ids:
            return
        # allow prefix match (e.g. tags)
        if any(
            mid == model_id or mid.startswith(f"{model_id}:") or model_id.startswith(f"{mid}")
            for mid in ids
        ):
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
    base_url: str | None = None,
    **kwargs: Any,
) -> ModelProvider:
    """Factory for provider backends."""
    key = (name or "").strip().lower()
    if key in {"mock", "dummy"}:
        from ethiocontexteval.providers.mock_provider import MockProvider

        return MockProvider(**kwargs)
    if key in {"ollama", "local"}:
        from ethiocontexteval.providers.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=base_url or "http://localhost:11434", **kwargs)
    if key in {"bedrock", "aws", "amazon"}:
        from ethiocontexteval.providers.bedrock_provider import BedrockProvider

        return BedrockProvider(region_name=region or "us-east-1", **kwargs)
    raise ProviderError(
        f"Unknown provider '{name}'. Supported: mock, ollama, bedrock."
    )

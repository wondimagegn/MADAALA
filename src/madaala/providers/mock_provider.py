"""Deterministic mock provider for tests, CI, and offline dry development."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from madaala.providers.base import GenerationResult, ModelInfo, ModelProvider

# Clearly non-scientific synthetic markers
MOCK_PREFIX = "[MOCK — not an experimental research result] "


class MockProvider(ModelProvider):
    """Returns predictable synthetic text. Never treat as pilot findings."""

    def __init__(self, models: list[str] | None = None) -> None:
        self._models = models or ["mock-model-a", "mock-model-b"]

    def provider_name(self) -> str:
        return "mock"

    def health_check(self) -> dict[str, Any]:
        return {
            "ok": True,
            "message": "MockProvider is always healthy (no external services).",
            "provider": "mock",
        }

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(model_id=mid, name=mid, provider="mock", metadata={"synthetic": True})
            for mid in self._models
        ]

    def generate(
        self,
        model_id: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 500,
        **kwargs: Any,
    ) -> GenerationResult:
        started = time.perf_counter()
        ts = datetime.now(UTC).isoformat()
        # tiny deterministic body from prompt length — not a real model answer
        snippet = (prompt or "").strip().replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        text = (
            f"{MOCK_PREFIX}provider=mock model_id={model_id} "
            f"temperature={temperature} max_tokens={max_tokens}. "
            f"Echo context: {snippet}"
        )
        latency = time.perf_counter() - started
        return GenerationResult(
            provider="mock",
            model_id=model_id,
            response=text,
            latency_seconds=round(latency, 6),
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            finish_reason="mock_stop",
            timestamp=ts,
            status="ok",
            error=None,
            provider_metadata={"synthetic": True, "note": "Not experimental data"},
        )

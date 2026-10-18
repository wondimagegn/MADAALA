"""Provider abstraction tests (no AWS, no live Ollama)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethiocontexteval.config import ModelConfig, PilotConfig
from ethiocontexteval.providers import (
    GenerationResult,
    ModelProvider,
    ProviderError,
    get_provider,
)
from ethiocontexteval.providers.mock_provider import MOCK_PREFIX, MockProvider
from ethiocontexteval.runner import run_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_get_provider_factory():
    assert get_provider("mock").provider_name() == "mock"
    with pytest.raises(ProviderError):
        get_provider("ollama")
    with pytest.raises(ProviderError):
        get_provider("unknown-cloud")


def test_mock_provider_health_and_generate():
    p = MockProvider()
    assert p.health_check()["ok"] is True
    models = p.list_models()
    assert len(models) >= 1
    result = p.generate("mock-model-a", "Hello Ethiopian context", temperature=0.0)
    assert isinstance(result, GenerationResult)
    assert result.status == "ok"
    assert result.provider == "mock"
    assert result.response is not None
    assert MOCK_PREFIX in result.response
    assert result.input_tokens is None  # never invent tokens
    assert result.provider_metadata.get("synthetic") is True


def test_mock_provider_is_model_provider_abc():
    assert isinstance(MockProvider(), ModelProvider)


def test_runner_execute_with_mock_writes_normalized_rows(tmp_path: Path):
    out = tmp_path / "gen.jsonl"
    cfg = PilotConfig(
        provider="mock",
        runs=1,
        max_tokens=50,
        temperature=0.0,
        dataset_path=ROOT / "data" / "pilot_scenarios_en.jsonl",
        results_dir=tmp_path,
        models=[ModelConfig(name="mock-a", model_id="mock-model-a", enabled=True)],
    )
    # Limit to first scenario via filtering: run full 12 is ok for mock speed
    path = run_experiment(
        cfg,
        output_path=out,
        verify_models=True,
        provider=get_provider("mock"),
    )
    assert path.is_file()
    lines = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(lines) == 12  # 12 scenarios x 1 model x 1 run
    row = lines[0]
    for key in (
        "response_id",
        "scenario_id",
        "provider",
        "model_id",
        "response",
        "latency_seconds",
        "status",
        "provider_metadata",
    ):
        assert key in row
    assert row["provider"] == "mock"
    assert row["status"] == "ok"
    assert MOCK_PREFIX in row["response"]

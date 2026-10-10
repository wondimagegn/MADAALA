"""Provider abstraction tests (no AWS, no live Ollama)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError

import pytest

from ethiocontexteval.config import ModelConfig, PilotConfig
from ethiocontexteval.providers import (
    GenerationResult,
    ModelProvider,
    ProviderError,
    get_provider,
)
from ethiocontexteval.providers.mock_provider import MOCK_PREFIX, MockProvider
from ethiocontexteval.providers.ollama_provider import OllamaProvider
from ethiocontexteval.runner import run_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_get_provider_factory():
    assert get_provider("mock").provider_name() == "mock"
    assert get_provider("ollama").provider_name() == "ollama"
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


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ollama_list_and_generate_with_mocked_http():
    calls: list[str] = []

    def fake_open(req, timeout=0):  # noqa: ARG001
        url = req.full_url if hasattr(req, "full_url") else str(req.get_full_url())
        calls.append(url)
        if url.endswith("/api/tags"):
            return _FakeResponse(
                {
                    "models": [
                        {"name": "qwen2.5:7b", "size": 1},
                        {"name": "gemma3:4b", "size": 2},
                    ]
                }
            )
        if url.endswith("/api/generate"):
            return _FakeResponse(
                {
                    "model": "qwen2.5:7b",
                    "response": "Local test answer",
                    "done": True,
                    "done_reason": "stop",
                    "prompt_eval_count": 12,
                    "eval_count": 8,
                }
            )
        raise AssertionError(f"unexpected url {url}")

    provider = OllamaProvider(base_url="http://localhost:11434", open_url=fake_open)
    health = provider.health_check()
    assert health["ok"] is True
    ids = {m.model_id for m in provider.list_models()}
    assert "qwen2.5:7b" in ids
    provider.ensure_model_available("qwen2.5:7b")
    result = provider.generate("qwen2.5:7b", "prompt text", max_tokens=50)
    assert result.status == "ok"
    assert result.response == "Local test answer"
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    assert result.total_tokens == 20
    assert result.finish_reason == "stop"
    assert result.provider == "ollama"


def test_ollama_health_failure_when_unreachable():
    def boom(req, timeout=0):  # noqa: ARG001
        raise URLError("connection refused")

    provider = OllamaProvider(open_url=boom)
    health = provider.health_check()
    assert health["ok"] is False
    assert "Cannot reach Ollama" in health["message"]


def test_ollama_does_not_auto_claim_missing_model():
    def fake_open(req, timeout=0):  # noqa: ARG001
        return _FakeResponse({"models": [{"name": "llama3.2:3b"}]})

    provider = OllamaProvider(open_url=fake_open)
    with pytest.raises(ProviderError, match="not installed"):
        provider.ensure_model_available("qwen2.5:7b")


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
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
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

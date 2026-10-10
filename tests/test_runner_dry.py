"""Dry-run planning tests (no AWS / no Ollama inference)."""

from __future__ import annotations

from pathlib import Path

from ethiocontexteval.config import ModelConfig, PilotConfig, load_config
from ethiocontexteval.dataset import load_scenarios
from ethiocontexteval.providers import get_provider
from ethiocontexteval.runner import dry_run_report, plan_requests

ROOT = Path(__file__).resolve().parents[1]


def test_plan_requests_english_only_pilot():
    scenarios = load_scenarios(ROOT / "data" / "scenarios.jsonl", strict=True)
    cfg = PilotConfig(
        provider="mock",
        runs=2,
        models=[
            ModelConfig(name="mock-a", model_id="mock-model-a", enabled=True),
            ModelConfig(name="mock-b", model_id="mock-model-b", enabled=True),
        ],
        dataset_path=ROOT / "data" / "scenarios.jsonl",
    )
    jobs = plan_requests(scenarios, cfg)
    # 12 executable EN x 2 models x 2 runs = 48
    assert len(jobs) == 48
    assert all(j["language"] == "en" for j in jobs)


def test_dry_run_report_with_mock_provider():
    cfg = PilotConfig(
        provider="mock",
        runs=2,
        models=[
            ModelConfig(name="mock-a", model_id="mock-model-a", enabled=True),
            ModelConfig(name="mock-b", model_id="mock-model-b", enabled=True),
        ],
        dataset_path=ROOT / "data" / "scenarios.jsonl",
        models_config_path=ROOT / "config" / "models.mock.json",
    )
    provider = get_provider("mock")
    report = dry_run_report(cfg, provider=provider, check_models=True)
    assert report["provider"] == "mock"
    assert report["executable_records"] == 12
    assert report["expected_generations"] == 48
    assert report["total_records"] == 36
    assert "English" in report["executable_languages"]
    assert "Amharic" in report["skipped"]
    assert "Afaan Oromo" in report["skipped"]
    assert report["provider_health"]["ok"] is True


def test_load_config_prefers_local_models_file():
    cfg = load_config(models_config_path=ROOT / "config" / "models.local.json")
    assert cfg.provider == "ollama"
    assert len(cfg.enabled_models()) == 2

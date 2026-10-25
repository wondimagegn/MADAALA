"""Dry-run planning tests (no AWS / no Ollama inference)."""

from __future__ import annotations

from pathlib import Path

from madaala.config import ModelConfig, PilotConfig, load_config
from madaala.dataset import load_scenarios
from madaala.providers import get_provider
from madaala.runner import dry_run_report, plan_requests

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
    cfg = load_config(models_config_path=ROOT / "config" / "models.mock.json")
    assert cfg.provider == "mock"
    assert len(cfg.enabled_models()) == 2


def test_madaala_environment_overrides(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    overrides = {
        "MADAALA_CONFIG": str(ROOT / "config" / "models.mock.json"),
        "MADAALA_PROVIDER": "mock",
        "MADAALA_RUNS": "3",
        "MADAALA_MAX_TOKENS": "321",
        "MADAALA_TEMPERATURE": "0.25",
        "MADAALA_DATASET": str(tmp_path / "scenarios.jsonl"),
        "MADAALA_RESULTS": str(tmp_path / "results"),
        "MADAALA_ALLOW_UNVALIDATED": "true",
    }
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)

    cfg = load_config(dotenv_path=env_file)

    assert cfg.provider == "mock"
    assert cfg.models_config_path == ROOT / "config" / "models.mock.json"
    assert cfg.runs == 3
    assert cfg.max_tokens == 321
    assert cfg.temperature == 0.25
    assert cfg.dataset_path == tmp_path / "scenarios.jsonl"
    assert cfg.results_dir == tmp_path / "results"
    assert cfg.allow_unvalidated is True

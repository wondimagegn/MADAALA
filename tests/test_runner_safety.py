"""CLI and research safeguards tested without AWS."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from madaala.config import ModelConfig, PilotConfig
from madaala.dataset import executable_scenarios, is_research_grade, load_scenarios
from madaala.runner import dry_run_report, main, run_experiment

ROOT = Path(__file__).resolve().parents[1]


def test_exact_filter_and_unknown_model():
    cfg = PilotConfig(provider="mock", runs=1, models=[ModelConfig("mock-a", "mock-model-a")])
    report = dry_run_report(cfg, scenario_id="EDU-001", language="en", model_id="mock-model-a")
    assert report["expected_generations"] == 1
    with pytest.raises(ValueError):
        dry_run_report(cfg, model_id="missing")
    with pytest.raises(ValueError):
        dry_run_report(cfg, scenario_id="missing")


def test_validation_metadata_controls_research_grade():
    rows = load_scenarios(ROOT / "data/scenarios.jsonl")
    assert len(executable_scenarios(rows, allow_unvalidated=True)) == 36
    assert not any(is_research_grade(r) for r in rows)
    row = replace(
        rows[0], translation_status="expert_validated", validation_status="expert_validated"
    )
    assert is_research_grade(row)


def test_cli_dry_run_never_initializes_provider(monkeypatch):
    monkeypatch.setattr(
        "madaala.runner.create_provider_from_config",
        lambda _: pytest.fail("provider initialized"),
    )
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--provider",
                "bedrock",
                "--config",
                str(ROOT / "config/models.bedrock.example.json"),
                "--dry-run",
            ]
        )
    assert exc.value.code == 0


def test_mock_technical_and_resume(tmp_path):
    cfg = PilotConfig(
        provider="mock",
        runs=1,
        allow_unvalidated=True,
        models=[ModelConfig("mock-a", "mock-model-a")],
    )
    out = tmp_path / "nested/result.jsonl"
    run_experiment(cfg, output_path=out, scenario_id="EDU-001", language="am")
    run_experiment(cfg, output_path=out, scenario_id="EDU-001", language="am")
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["technical_pilot"]
    assert not rows[0]["research_grade"]
    assert rows[0]["validation_status_at_run"] == "pending_expert_validation"

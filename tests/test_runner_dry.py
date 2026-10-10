"""Dry-run planning tests (no AWS calls)."""

from __future__ import annotations

from pathlib import Path

from ethiocontexteval.config import ModelConfig, PilotConfig
from ethiocontexteval.dataset import load_scenarios
from ethiocontexteval.runner import dry_run_report, plan_requests

ROOT = Path(__file__).resolve().parents[1]


def test_plan_requests_english_only_pilot():
    scenarios = load_scenarios(ROOT / "data" / "scenarios.jsonl", strict=True)
    cfg = PilotConfig(
        runs=2,
        models=[
            ModelConfig(name="nova-lite", model_id="amazon.nova-lite-v1:0", enabled=True),
            ModelConfig(name="nova-pro", model_id="amazon.nova-pro-v1:0", enabled=True),
        ],
        dataset_path=ROOT / "data" / "scenarios.jsonl",
    )
    jobs = plan_requests(scenarios, cfg)
    # 12 executable EN × 2 models × 2 runs = 48
    assert len(jobs) == 48
    assert all(j["language"] == "en" for j in jobs)


def test_dry_run_report_counts():
    cfg = PilotConfig(
        runs=2,
        models=[
            ModelConfig(name="nova-lite", model_id="amazon.nova-lite-v1:0", enabled=True),
            ModelConfig(name="nova-pro", model_id="amazon.nova-pro-v1:0", enabled=True),
        ],
        dataset_path=ROOT / "data" / "scenarios.jsonl",
    )
    report = dry_run_report(cfg)
    assert report["executable_records"] == 12
    assert report["expected_api_requests"] == 48
    assert report["total_records"] == 36

"""Tests for dataset loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from madaala.dataset import (
    DatasetValidationError,
    executable_scenarios,
    load_scenarios,
    validate_dataset,
)

ROOT = Path(__file__).resolve().parents[1]


def test_pilot_english_dataset_valid():
    path = ROOT / "data" / "pilot_scenarios_en.jsonl"
    scenarios = load_scenarios(path, strict=True)
    assert len(scenarios) == 12
    ids = {s.scenario_id for s in scenarios}
    assert ids == {
        "EDU-001",
        "EDU-002",
        "EDU-003",
        "GOV-001",
        "GOV-002",
        "GOV-003",
        "BUS-001",
        "BUS-002",
        "BUS-003",
        "CTX-001",
        "CTX-002",
        "CTX-003",
    }
    assert all(s.language == "en" for s in scenarios)
    assert len(executable_scenarios(scenarios)) == 12


def test_multilingual_template_valid_and_pending_not_executable():
    path = ROOT / "data" / "scenarios.jsonl"
    scenarios = load_scenarios(path, strict=True)
    assert len(scenarios) == 36  # 12 x 3 languages
    exe = executable_scenarios(scenarios)
    assert len(exe) == 12
    assert all(s.language == "en" for s in exe)
    pending = [s for s in scenarios if s.language in {"am", "om"}]
    assert len(pending) == 24
    assert all(s.prompt for s in pending)
    assert all(not s.is_executable() for s in pending)


def test_validate_dataset_cli_path_ok():
    errors = validate_dataset(ROOT / "data" / "scenarios.jsonl")
    assert errors == []


def test_duplicate_rejected(tmp_path: Path):
    row = {
        "scenario_id": "EDU-001",
        "domain": "education",
        "difficulty": 2,
        "language": "en",
        "variant": "standard",
        "prompt": "Hello",
        "expected_behavior": ["a"],
        "cultural_dependency": False,
        "safety_sensitive": False,
        "translation_status": "master_english",
        "validation_status": "pending_expert_validation",
    }
    path = tmp_path / "dup.jsonl"
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError):
        load_scenarios(path, strict=True)


def test_untranslated_with_prompt_rejected(tmp_path: Path):
    row = {
        "scenario_id": "EDU-001",
        "domain": "education",
        "difficulty": 2,
        "language": "am",
        "variant": "standard",
        "prompt": "should not be present yet",
        "expected_behavior": ["a"],
        "cultural_dependency": True,
        "safety_sensitive": False,
        "translation_status": "pending_human_translation",
        "validation_status": "pending_expert_validation",
    }
    path = tmp_path / "bad_am.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    scenarios = load_scenarios(path, strict=True)
    assert not scenarios[0].is_executable()
    assert executable_scenarios(scenarios, allow_unvalidated=True) == scenarios


def test_empty_expected_behavior_rejected(tmp_path: Path):
    row = {
        "scenario_id": "EDU-001",
        "domain": "education",
        "difficulty": 2,
        "language": "en",
        "variant": "standard",
        "prompt": "Hello",
        "expected_behavior": [],
        "cultural_dependency": False,
        "safety_sensitive": False,
        "translation_status": "master_english",
        "validation_status": "pending_expert_validation",
    }
    path = tmp_path / "bad_eb.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError):
        load_scenarios(path, strict=True)


def test_unsupported_language_rejected(tmp_path: Path):
    row = {
        "scenario_id": "EDU-001",
        "domain": "education",
        "difficulty": 2,
        "language": "fr",
        "variant": "standard",
        "prompt": "Bonjour",
        "expected_behavior": ["a"],
        "cultural_dependency": False,
        "safety_sensitive": False,
        "translation_status": "master_english",
        "validation_status": "pending_expert_validation",
    }
    path = tmp_path / "bad_lang.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError):
        load_scenarios(path, strict=True)

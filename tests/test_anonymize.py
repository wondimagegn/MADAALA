"""Tests for response blinding."""

from __future__ import annotations

from madaala.anonymize import anonymize_generations


def test_anonymize_strips_model_and_provider_identity():
    generations = [
        {
            "response_id": "r1",
            "scenario_id": "EDU-001",
            "domain": "education",
            "language": "en",
            "variant": "standard",
            "run": 1,
            "provider": "ollama",
            "model_id": "qwen2.5:7b",
            "model_name": "qwen-local",
            "response": "Answer A",
            "status": "ok",
        },
        {
            "response_id": "r2",
            "scenario_id": "EDU-001",
            "domain": "education",
            "language": "en",
            "variant": "standard",
            "run": 1,
            "provider": "ollama",
            "model_id": "gemma3:4b",
            "model_name": "gemma-local",
            "response": "Answer B",
            "status": "ok",
        },
        {
            "response_id": "r3",
            "scenario_id": "EDU-002",
            "domain": "education",
            "language": "en",
            "run": 1,
            "provider": "ollama",
            "model_id": "qwen2.5:7b",
            "response": None,
            "status": "error",
        },
    ]
    blinded, mapping = anonymize_generations(generations)
    assert len(blinded) == 2
    assert len(mapping) == 2
    for row in blinded:
        assert "model_id" not in row
        assert "model_name" not in row
        assert "provider" not in row
        assert row["blind_id"].startswith("B-")
        assert row["response"] in {"Answer A", "Answer B"}
    assert {m["provider"] for m in mapping} == {"ollama"}
    map_models = {m["model_id"] for m in mapping}
    assert map_models == {"qwen2.5:7b", "gemma3:4b"}
    assert {m["response_id"] for m in mapping} == {"r1", "r2"}


def test_blind_ids_unique():
    generations = [
        {
            "response_id": f"r{i}",
            "scenario_id": "GOV-001",
            "domain": "public_services",
            "language": "en",
            "run": 1,
            "provider": "mock",
            "model_id": "m",
            "response": f"text {i}",
            "status": "ok",
        }
        for i in range(5)
    ]
    blinded, mapping = anonymize_generations(generations)
    ids = [b["blind_id"] for b in blinded]
    assert len(ids) == len(set(ids))
    assert len(mapping) == 5
    assert all(m.get("provider") == "mock" for m in mapping)

"""Tests for response blinding."""

from __future__ import annotations

from ethiocontexteval.anonymize import anonymize_generations


def test_anonymize_strips_model_identity():
    generations = [
        {
            "response_id": "r1",
            "scenario_id": "EDU-001",
            "domain": "education",
            "language": "en",
            "variant": "standard",
            "run": 1,
            "model_id": "amazon.nova-lite-v1:0",
            "model_name": "nova-lite",
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
            "model_id": "amazon.nova-pro-v1:0",
            "model_name": "nova-pro",
            "response": "Answer B",
            "status": "ok",
        },
        {
            "response_id": "r3",
            "scenario_id": "EDU-002",
            "domain": "education",
            "language": "en",
            "run": 1,
            "model_id": "amazon.nova-lite-v1:0",
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
    map_models = {m["model_id"] for m in mapping}
    assert map_models == {"amazon.nova-lite-v1:0", "amazon.nova-pro-v1:0"}
    # mapping links blind_id to response_id
    assert {m["response_id"] for m in mapping} == {"r1", "r2"}


def test_blind_ids_unique():
    generations = [
        {
            "response_id": f"r{i}",
            "scenario_id": "GOV-001",
            "domain": "public_services",
            "language": "en",
            "run": 1,
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

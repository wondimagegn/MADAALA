"""Tests for evaluation metrics."""

from __future__ import annotations

from ethiocontexteval.metrics import (
    context_fidelity_gap,
    language_parity_gap,
    mean_score_by_domain,
    mean_score_by_language,
    mean_score_by_model,
    normalized_language_parity_gap,
    robustness_gap,
    row_composite_score,
    safety_consistency_gap,
)


def _row(**kwargs):
    base = {
        "language": "en",
        "domain": "education",
        "model_id": "amazon.nova-lite-v1:0",
        "correctness": 4,
        "context_fidelity": 4,
        "instruction_following": 4,
        "language_quality": 4,
        "usefulness": 4,
        "safety": None,
        "variant": "standard",
    }
    base.update(kwargs)
    return base


def test_row_composite_mean():
    assert row_composite_score(_row(correctness=5, usefulness=3)) == 4.0


def test_mean_score_by_language():
    rows = [
        _row(
            language="en",
            correctness=5,
            context_fidelity=5,
            instruction_following=5,
            language_quality=5,
            usefulness=5,
        ),
        _row(
            language="am",
            correctness=3,
            context_fidelity=3,
            instruction_following=3,
            language_quality=3,
            usefulness=3,
        ),
    ]
    means = mean_score_by_language(rows)
    assert means["en"] == 5.0
    assert means["am"] == 3.0


def test_mean_score_by_model_and_domain():
    rows = [
        _row(model_id="m1", domain="education"),
        _row(
            model_id="m2",
            domain="education",
            correctness=2,
            context_fidelity=2,
            instruction_following=2,
            language_quality=2,
            usefulness=2,
        ),
        _row(model_id="m1", domain="public_services"),
    ]
    by_model = mean_score_by_model(rows)
    assert "m1" in by_model and "m2" in by_model
    assert by_model["m2"] == 2.0
    by_domain = mean_score_by_domain(rows)
    assert "education" in by_domain


def test_language_parity_gap():
    scores = {"en": 4.0, "am": 3.0, "om": 2.0}
    lpg = language_parity_gap(scores)
    assert lpg["en"] == 0.0
    assert lpg["am"] == 1.0
    assert lpg["om"] == 2.0


def test_normalized_lpg_zero_denominator():
    scores = {"en": 0.0, "am": 0.0}
    nlpg = normalized_language_parity_gap(scores)
    assert nlpg["en"] == 0.0
    assert nlpg["am"] is None  # avoid misleading percentage


def test_normalized_lpg_normal():
    scores = {"en": 4.0, "am": 2.0}
    nlpg = normalized_language_parity_gap(scores)
    assert nlpg["am"] == 0.5


def test_context_and_safety_gaps():
    rows = [
        _row(language="en", context_fidelity=5, safety=5),
        _row(language="am", context_fidelity=3, safety=4),
    ]
    cfg = context_fidelity_gap(rows)
    assert cfg["am"] == 2.0
    sg = safety_consistency_gap(rows)
    assert sg["am"] == 1.0


def test_robustness_gap():
    rows = [
        _row(
            variant="standard",
            correctness=5,
            context_fidelity=5,
            instruction_following=5,
            language_quality=5,
            usefulness=5,
        ),
        _row(
            variant="paraphrase",
            correctness=3,
            context_fidelity=3,
            instruction_following=3,
            language_quality=3,
            usefulness=3,
        ),
    ]
    gap = robustness_gap(rows, other_variant="paraphrase")
    assert gap == 2.0
    assert robustness_gap(rows, other_variant="missing") is None

"""Evaluation metrics for MADAALA pilot scores."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import numpy as np

# Primary composite uses these dimensions when present
DEFAULT_SCORE_DIMENSIONS = (
    "correctness",
    "context_fidelity",
    "instruction_following",
    "language_quality",
    "usefulness",
)


def row_composite_score(
    row: dict[str, Any],
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> float | None:
    """Mean of available 1-5 dimensions for one rating row (safety excluded by default)."""
    vals = []
    for dim in dimensions:
        v = row.get(dim)
        if v is not None:
            vals.append(float(v))
    if not vals:
        return None
    return float(np.mean(vals))


def _group_means(
    rows: Sequence[dict[str, Any]],
    key_fn,
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> dict[Any, float]:
    buckets: dict[Any, list[float]] = defaultdict(list)
    for row in rows:
        score = row_composite_score(row, dimensions)
        if score is None:
            continue
        buckets[key_fn(row)].append(score)
    return {k: float(np.mean(v)) for k, v in sorted(buckets.items(), key=lambda kv: str(kv[0]))}


def mean_score_by_language(
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> dict[str, float]:
    return _group_means(rows, lambda r: str(r.get("language", "")).lower(), dimensions)


def mean_score_by_model(
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> dict[str, float]:
    def key(r: dict[str, Any]) -> str:
        return str(r.get("model_id") or r.get("model_name") or r.get("model") or "unknown")

    return _group_means(rows, key, dimensions)


def mean_score_by_domain(
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> dict[str, float]:
    return _group_means(rows, lambda r: str(r.get("domain") or "unknown"), dimensions)


def mean_score_by_dimension(rows: Sequence[dict[str, Any]]) -> dict[str, float]:
    dims = list(DEFAULT_SCORE_DIMENSIONS) + ["safety"]
    out: dict[str, float] = {}
    for dim in dims:
        vals = [float(r[dim]) for r in rows if r.get(dim) is not None]
        if vals:
            out[dim] = float(np.mean(vals))
    return out


def language_parity_gap(
    scores_by_language: dict[str, float],
    *,
    reference_language: str = "en",
) -> dict[str, float | None]:
    """
    LPG_l = S_English - S_l

    Positive values mean the reference language scored higher.
    """
    ref = scores_by_language.get(reference_language)
    out: dict[str, float | None] = {}
    for lang, score in scores_by_language.items():
        if lang == reference_language:
            out[lang] = 0.0
            continue
        if ref is None:
            out[lang] = None
        else:
            out[lang] = float(ref - score)
    return out


def normalized_language_parity_gap(
    scores_by_language: dict[str, float],
    *,
    reference_language: str = "en",
) -> dict[str, float | None]:
    """
    NLPG_l = (S_English - S_l) / S_English

    Returns None when the English denominator is zero or missing.
    """
    ref = scores_by_language.get(reference_language)
    out: dict[str, float | None] = {}
    for lang, score in scores_by_language.items():
        if lang == reference_language:
            out[lang] = 0.0
            continue
        if ref is None or ref == 0:
            out[lang] = None
        else:
            out[lang] = float((ref - score) / ref)
    return out


def context_fidelity_gap(
    rows: Sequence[dict[str, Any]],
    *,
    reference_language: str = "en",
) -> dict[str, float | None]:
    """Gap on context_fidelity dimension only: S_en - S_l."""
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        v = row.get("context_fidelity")
        if v is None:
            continue
        lang = str(row.get("language", "")).lower()
        buckets[lang].append(float(v))
    means = {k: float(np.mean(v)) for k, v in buckets.items()}
    return language_parity_gap(means, reference_language=reference_language)


def safety_consistency_gap(
    rows: Sequence[dict[str, Any]],
    *,
    reference_language: str = "en",
) -> dict[str, float | None]:
    """Gap on safety dimension: S_en - S_l (nullable safety excluded)."""
    buckets: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        v = row.get("safety")
        if v is None:
            continue
        lang = str(row.get("language", "")).lower()
        buckets[lang].append(float(v))
    if not buckets:
        return {}
    means = {k: float(np.mean(v)) for k, v in buckets.items()}
    return language_parity_gap(means, reference_language=reference_language)


def robustness_gap(
    rows: Sequence[dict[str, Any]],
    *,
    base_variant: str = "standard",
    other_variant: str,
    dimensions: Sequence[str] = DEFAULT_SCORE_DIMENSIONS,
) -> float | None:
    """
    Mean composite(base) - mean composite(other) for future variant studies.

    Returns None if either variant has no scores.
    """
    base_scores = [
        s
        for r in rows
        if str(r.get("variant") or "standard") == base_variant
        for s in [row_composite_score(r, dimensions)]
        if s is not None
    ]
    other_scores = [
        s
        for r in rows
        if str(r.get("variant") or "") == other_variant
        for s in [row_composite_score(r, dimensions)]
        if s is not None
    ]
    if not base_scores or not other_scores:
        return None
    return float(np.mean(base_scores) - np.mean(other_scores))


def count_error_codes(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        codes = row.get("error_codes") or []
        if isinstance(codes, str):
            codes = [c.strip() for c in codes.replace(";", ",").split(",") if c.strip()]
        for code in codes:
            counts[str(code).upper()] += 1
    return dict(sorted(counts.items()))


def attach_model_from_mapping(
    ratings: Sequence[dict[str, Any]],
    mapping_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join ratings to private blind mapping to recover model_id for analysis."""
    by_blind = {str(m["blind_id"]): m for m in mapping_rows if m.get("blind_id")}
    out = []
    for r in ratings:
        merged = dict(r)
        m = by_blind.get(str(r.get("blind_id")))
        if m:
            merged["provider"] = m.get("provider")
            merged["model_id"] = m.get("model_id")
            merged["model_name"] = m.get("model_name")
            merged["response_id"] = m.get("response_id")
        out.append(merged)
    return out

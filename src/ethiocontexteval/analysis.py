"""Statistical analysis and report generation for EthioContextEval pilot."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from ethiocontexteval.config import load_config, repo_root
from ethiocontexteval.human_evaluation import ERROR_TAXONOMY, load_all_ratings
from ethiocontexteval.metrics import (
    attach_model_from_mapping,
    context_fidelity_gap,
    count_error_codes,
    language_parity_gap,
    mean_score_by_dimension,
    mean_score_by_domain,
    mean_score_by_language,
    mean_score_by_model,
    normalized_language_parity_gap,
    row_composite_score,
    safety_consistency_gap,
)

PILOT_WARNING = (
    "WARNING: This is a feasibility pilot with a small scenario set (n~12 masters). "
    "Statistical power is limited. Do not generalize results to all generative AI models "
    "or to all Ethiopian language varieties. Human expert validation of translations and "
    "ratings is required before scientific interpretation."
)


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) via percentile bootstrap."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n_boot):
        sample = rng.choice(arr, size=arr.size, replace=True)
        means.append(float(np.mean(sample)))
    low = float(np.percentile(means, 100 * alpha / 2))
    high = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return float(np.mean(arr)), low, high


def paired_language_comparison(
    rows: Sequence[dict[str, Any]],
    *,
    reference_language: str = "en",
    other_language: str,
    group_keys: Sequence[str] = ("scenario_id", "model_id", "run", "evaluator_id"),
) -> dict[str, Any]:
    """
    Pair scores by matched scenario (and model/run/evaluator when present).

    Uses Wilcoxon signed-rank when pairs >= 6; otherwise reports descriptive only.
    """
    def key_of(r: dict[str, Any]) -> tuple:
        return tuple(str(r.get(k) or "") for k in group_keys)

    ref_map: dict[tuple, float] = {}
    other_map: dict[tuple, float] = {}
    for r in rows:
        score = row_composite_score(r)
        if score is None:
            continue
        lang = str(r.get("language", "")).lower()
        k = key_of(r)
        # For pairing across languages, drop language from key — rebuild without language
        k2 = tuple(str(r.get(k0) or "") for k0 in group_keys)
        if lang == reference_language:
            ref_map[k2] = score
        elif lang == other_language:
            other_map[k2] = score

    pairs = []
    for k, rv in ref_map.items():
        if k in other_map:
            pairs.append((rv, other_map[k]))

    if not pairs:
        return {
            "reference_language": reference_language,
            "other_language": other_language,
            "n_pairs": 0,
            "mean_ref": None,
            "mean_other": None,
            "mean_diff": None,
            "wilcoxon_stat": None,
            "wilcoxon_p": None,
            "effect_size_r": None,
            "note": "No matched pairs found",
        }

    diffs = np.array([a - b for a, b in pairs], dtype=float)
    mean_ref = float(np.mean([a for a, _ in pairs]))
    mean_other = float(np.mean([b for _, b in pairs]))
    result: dict[str, Any] = {
        "reference_language": reference_language,
        "other_language": other_language,
        "n_pairs": len(pairs),
        "mean_ref": mean_ref,
        "mean_other": mean_other,
        "mean_diff": float(np.mean(diffs)),
        "wilcoxon_stat": None,
        "wilcoxon_p": None,
        "effect_size_r": None,
        "note": PILOT_WARNING,
    }

    # Wilcoxon requires non-zero differences ideally
    nonzero = diffs[diffs != 0]
    if len(pairs) >= 6 and nonzero.size > 0:
        try:
            stat, p = stats.wilcoxon(nonzero)
            result["wilcoxon_stat"] = float(stat)
            result["wilcoxon_p"] = float(p)
            n = nonzero.size
            # effect size r = Z / sqrt(N); approximate Z from p for two-sided
            if p is not None and 0 < p < 1:
                z = stats.norm.ppf(1 - p / 2)
                result["effect_size_r"] = float(z / math.sqrt(n)) if n else None
        except ValueError as exc:
            result["note"] = f"Wilcoxon not applicable: {exc}. {PILOT_WARNING}"
    else:
        result["note"] = (
            f"Fewer than 6 pairs or no nonzero diffs (n={len(pairs)}); "
            f"inferential test skipped. {PILOT_WARNING}"
        )
    return result


def percentage_agreement(
    ratings_a: Sequence[dict[str, Any]],
    ratings_b: Sequence[dict[str, Any]],
    *,
    dimension: str = "correctness",
    id_key: str = "blind_id",
) -> float | None:
    """Simple percentage agreement on one dimension for matched blind_ids."""
    map_a = {str(r[id_key]): r.get(dimension) for r in ratings_a if r.get(id_key)}
    map_b = {str(r[id_key]): r.get(dimension) for r in ratings_b if r.get(id_key)}
    common = sorted(set(map_a) & set(map_b))
    if not common:
        return None
    agree = 0
    total = 0
    for k in common:
        va, vb = map_a[k], map_b[k]
        if va is None or vb is None:
            continue
        total += 1
        if va == vb:
            agree += 1
    if total == 0:
        return None
    return float(agree / total)


def krippendorff_alpha(
    rating_tables: Sequence[Sequence[dict[str, Any]]],
    *,
    dimension: str = "correctness",
    id_key: str = "blind_id",
    level: str = "ordinal",
) -> float | None:
    """
    Krippendorff's alpha for ordinal ratings across evaluators.

    Lightweight implementation (no extra dependency). Returns None if insufficient data.
    """
    # Build item -> list of ratings from different evaluators
    item_ratings: dict[str, list[float]] = defaultdict(list)
    for table in rating_tables:
        for row in table:
            bid = str(row.get(id_key) or "")
            val = row.get(dimension)
            if not bid or val is None:
                continue
            item_ratings[bid].append(float(val))

    # Keep items with at least 2 ratings
    items = {k: v for k, v in item_ratings.items() if len(v) >= 2}
    if len(items) < 2:
        return None

    all_vals = [v for vs in items.values() for v in vs]
    if not all_vals:
        return None

    # Coincidence matrix approach for ordinal metric
    # Flatten pair coincidences within items
    value_set = sorted(set(all_vals))
    idx = {v: i for i, v in enumerate(value_set)}
    m = len(value_set)
    o = np.zeros((m, m), dtype=float)

    for vs in items.values():
        n_u = len(vs)
        if n_u < 2:
            continue
        for i in range(n_u):
            for j in range(n_u):
                if i == j:
                    continue
                o[idx[vs[i]], idx[vs[j]]] += 1.0 / (n_u - 1)

    n_total = o.sum()
    if n_total == 0:
        return None

    # Expected coincidences
    n_c = o.sum(axis=1)
    e = np.zeros_like(o)
    for c in range(m):
        for k in range(m):
            if n_total > 1:
                e[c, k] = n_c[c] * n_c[k] / (n_total - 1) if c != k else n_c[c] * (n_c[c] - 1) / (
                    n_total - 1
                )

    # Ordinal distance
    def delta(c: int, k: int) -> float:
        if c == k:
            return 0.0
        # number of values between and including
        lo, hi = min(c, k), max(c, k)
        # standard ordinal distance: (cumulative midpoints difference)^2 simplified:
        return float((hi - lo) ** 2)

    do = 0.0
    de = 0.0
    for c in range(m):
        for k in range(m):
            d = delta(c, k)
            do += o[c, k] * d
            de += e[c, k] * d
    if de == 0:
        return 1.0 if do == 0 else None
    return float(1.0 - (do / de))


def _load_mapping(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})


def generate_analysis_tables(
    ratings: Sequence[dict[str, Any]],
    analysis_dir: Path,
) -> dict[str, Path]:
    """Write summary CSVs under results/analysis/."""
    analysis_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    by_lang = mean_score_by_language(ratings)
    by_model = mean_score_by_model(ratings)
    by_domain = mean_score_by_domain(ratings)
    by_dim = mean_score_by_dimension(ratings)
    lpg = language_parity_gap(by_lang)
    nlpg = normalized_language_parity_gap(by_lang)
    cfg_gap = context_fidelity_gap(ratings)
    safety_gap = safety_consistency_gap(ratings)
    errors = count_error_codes(ratings)

    # descriptive bootstrap CIs per language
    lang_rows = []
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in ratings:
        s = row_composite_score(r)
        if s is None:
            continue
        buckets[str(r.get("language", "")).lower()].append(s)
    for lang, vals in sorted(buckets.items()):
        mean, lo, hi = bootstrap_mean_ci(vals)
        lang_rows.append(
            {
                "language": lang,
                "n": len(vals),
                "mean_score": mean,
                "ci95_low": lo,
                "ci95_high": hi,
                "lpg": lpg.get(lang),
                "nlpg": nlpg.get(lang),
            }
        )
    p = analysis_dir / "language_scores.csv"
    _write_csv(p, lang_rows)
    paths["language_scores"] = p

    domain_rows = [{"domain": k, "mean_score": v} for k, v in by_domain.items()]
    p = analysis_dir / "domain_scores.csv"
    _write_csv(p, domain_rows)
    paths["domain_scores"] = p

    parity_rows = []
    for lang in by_lang:
        parity_rows.append(
            {
                "language": lang,
                "mean_score": by_lang.get(lang),
                "lpg": lpg.get(lang),
                "nlpg": nlpg.get(lang),
                "context_fidelity_gap": cfg_gap.get(lang),
                "safety_consistency_gap": safety_gap.get(lang),
            }
        )
    p = analysis_dir / "parity_gaps.csv"
    _write_csv(p, parity_rows)
    paths["parity_gaps"] = p

    err_rows = [
        {"error_code": code, "description": ERROR_TAXONOMY.get(code, ""), "count": cnt}
        for code, cnt in errors.items()
    ]
    p = analysis_dir / "error_counts.csv"
    _write_csv(p, err_rows)
    paths["error_counts"] = p

    summary = [
        {"metric": "n_ratings", "value": len(ratings)},
        {"metric": "n_languages", "value": len(by_lang)},
        {"metric": "n_models", "value": len(by_model)},
        {"metric": "n_domains", "value": len(by_domain)},
    ]
    for dim, val in by_dim.items():
        summary.append({"metric": f"mean_{dim}", "value": val})
    for mid, val in by_model.items():
        summary.append({"metric": f"mean_model::{mid}", "value": val})
    p = analysis_dir / "summary.csv"
    _write_csv(p, summary)
    paths["summary"] = p

    return paths


def generate_figures(ratings: Sequence[dict[str, Any]], figures_dir: Path) -> list[Path]:
    """Create individual matplotlib charts (no seaborn, no subplots)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    by_lang = mean_score_by_language(ratings)
    if by_lang:
        fig, ax = plt.subplots()
        langs = list(by_lang.keys())
        vals = [by_lang[k] for k in langs]
        ax.bar(langs, vals)
        ax.set_xlabel("Language")
        ax.set_ylabel("Mean composite score")
        ax.set_title("Overall score by language (pilot)")
        ax.set_ylim(0, 5)
        path = figures_dir / "score_by_language.png"
        fig.savefig(path, bbox_inches="tight", dpi=120)
        plt.close(fig)
        written.append(path)

    # LPG by model if model_id present
    has_model = any(r.get("model_id") or r.get("model_name") for r in ratings)
    if has_model:
        # compute LPG per model
        models = sorted(
            {
                str(r.get("model_id") or r.get("model_name"))
                for r in ratings
                if r.get("model_id") or r.get("model_name")
            }
        )
        # For each model, LPG for non-en languages — plot mean |LPG| or LPG for am/om
        plot_labels = []
        plot_vals = []
        for mid in models:
            subset = [
                r
                for r in ratings
                if str(r.get("model_id") or r.get("model_name")) == mid
            ]
            scores = mean_score_by_language(subset)
            gaps = language_parity_gap(scores)
            for lang, gap in gaps.items():
                if lang == "en" or gap is None:
                    continue
                plot_labels.append(f"{mid}\n{lang}")
                plot_vals.append(gap)
        if plot_labels:
            fig, ax = plt.subplots()
            ax.bar(range(len(plot_labels)), plot_vals)
            ax.set_xticks(range(len(plot_labels)))
            ax.set_xticklabels(plot_labels, rotation=45, ha="right")
            ax.set_ylabel("Language Parity Gap (S_en - S_l)")
            ax.set_title("Language Parity Gap by model (pilot)")
            path = figures_dir / "lpg_by_model.png"
            fig.savefig(path, bbox_inches="tight", dpi=120)
            plt.close(fig)
            written.append(path)

    by_domain = mean_score_by_domain(ratings)
    if by_domain:
        fig, ax = plt.subplots()
        domains = list(by_domain.keys())
        vals = [by_domain[k] for k in domains]
        ax.bar(domains, vals)
        ax.set_xlabel("Domain")
        ax.set_ylabel("Mean composite score")
        ax.set_title("Score by domain (pilot)")
        ax.set_ylim(0, 5)
        plt.xticks(rotation=30, ha="right")
        path = figures_dir / "score_by_domain.png"
        fig.savefig(path, bbox_inches="tight", dpi=120)
        plt.close(fig)
        written.append(path)

    # Placeholder note chart only if automatic eval later — skip if no auto scores
    return written


def generate_report(
    *,
    ratings: Sequence[dict[str, Any]] | None,
    generations_meta: dict[str, Any] | None,
    output_path: Path,
    analysis_paths: dict[str, Path] | None = None,
) -> Path:
    """Generate reports/pilot_report.md from actual outputs or a clear template."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    has_results = bool(ratings)
    lines: list[str] = []
    lines.append("# EthioContextEval Pilot")
    lines.append("")
    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Assess the feasibility of human-grounded evaluation of multilingual generative AI "
        "for Ethiopian contexts (English, Amharic, Afaan Oromo), supporting the broader "
        "EthioContextEval research program and Amazon Research Awards proposal readiness."
    )
    lines.append("")
    lines.append("## Research Question")
    lines.append("")
    lines.append(
        "How do selected generative models behave on matched, context-sensitive tasks "
        "across English, Amharic, and Afaan Oromo, as judged by human evaluators on "
        "correctness, context fidelity, instruction following, language quality, usefulness, "
        "and safety?"
    )
    lines.append("")
    lines.append("## Experimental Design")
    lines.append("")
    lines.append(
        "- **Languages:** English (master), Amharic and Afaan Oromo (human translation pending)."
    )
    lines.append("- **Domains:** education, public services, business/finance, Ethiopian contextual reasoning.")
    lines.append("- **Design cell:** scenarios × languages × models × repeated generations.")
    lines.append("- **Inference:** Amazon Bedrock Converse API; temperature 0 by default.")
    lines.append("- **Blinding:** evaluators see responses without model identity.")
    lines.append("")
    lines.append("## Dataset")
    lines.append("")
    lines.append(
        "Twelve English master scenarios (`data/pilot_scenarios_en.jsonl`), expanded to a "
        "multilingual template (`data/scenarios.jsonl`) with Amharic and Afaan Oromo prompts "
        "left null until expert translation and validation. "
        "**No machine translation is treated as ground truth.**"
    )
    lines.append("")
    lines.append("## Models")
    lines.append("")
    cfg = load_config()
    for m in cfg.models:
        state = "enabled" if m.enabled else "disabled"
        lines.append(f"- `{m.name}`: `{m.model_id}` ({state})")
    lines.append("")
    lines.append(
        "Model availability must be verified per region via "
        "`python -m ethiocontexteval.models list`."
    )
    lines.append("")
    lines.append("## Human Evaluation")
    lines.append("")
    lines.append(
        "Independent raters score blinded responses on 1–5 Likert dimensions "
        "(see `docs/annotation-guidelines.md`). Error codes E1–E10 may be applied."
    )
    lines.append("")
    lines.append("## Statistical Methodology")
    lines.append("")
    lines.append(
        "Descriptive means by language/model/domain; Language Parity Gap (LPG) and "
        "Normalized LPG; bootstrap confidence intervals; Wilcoxon signed-rank on "
        "paired English–target language scores when pairs suffice; Krippendorff's alpha "
        "for multi-rater agreement. "
        "**Mixed-effects models are reserved for the full study.**"
    )
    lines.append("")
    lines.append(f"> {PILOT_WARNING}")
    lines.append("")
    lines.append("## Preliminary Results")
    lines.append("")
    if not has_results:
        lines.append(
            "_No human ratings are available yet. This section is a template only. "
            "Do not invent or impute experimental results._"
        )
    else:
        by_lang = mean_score_by_language(ratings or [])
        lines.append("Mean composite scores by language:")
        lines.append("")
        for lang, score in by_lang.items():
            lines.append(f"- **{lang}**: {score:.3f}")
        lines.append("")
        lines.append(f"> {PILOT_WARNING}")
        if analysis_paths:
            lines.append("")
            lines.append("Analysis artifacts:")
            for name, path in analysis_paths.items():
                lines.append(f"- {name}: `{path.as_posix()}`")
    lines.append("")
    lines.append("## Error Analysis")
    lines.append("")
    if not has_results:
        lines.append("_Pending ratings with error codes (E1–E10)._")
    else:
        counts = count_error_codes(ratings or [])
        if not counts:
            lines.append("No error codes recorded in current ratings.")
        else:
            for code, cnt in counts.items():
                desc = ERROR_TAXONOMY.get(code, "")
                lines.append(f"- {code} ({desc}): {cnt}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Small pilot scenario count (12 masters).")
    lines.append("- Amharic and Afaan Oromo prompts require expert translation before multilingual claims.")
    lines.append("- Limited statistical power; p-values are exploratory.")
    lines.append("- Model availability and behavior vary by AWS region and time.")
    lines.append("- Single-institution pilot evaluators may not represent all user communities.")
    lines.append("")
    lines.append("## Lessons Learned")
    lines.append("")
    lines.append(
        "_To be completed after the first end-to-end pilot cycle "
        "(generation → blinding → rating → analysis)._"
    )
    lines.append("")
    lines.append("## Implications for Full EthioContextEval Study")
    lines.append("")
    lines.append(
        "The pilot validates tooling, schema, blinding, and analysis pathways. "
        "The full study should expand scenario coverage, complete human translation "
        "and cultural validation, increase rater diversity, and apply mixed-effects "
        "models for crossed scenario/language/model factors."
    )
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("- Configuration via environment variables and `config/models*.json`.")
    lines.append("- Dataset validation: `python -m ethiocontexteval.dataset validate`.")
    lines.append("- Dry run: `python -m ethiocontexteval.runner --dry-run`.")
    lines.append("- Tests: `pytest`.")
    lines.append("- No AWS credentials are stored in the repository.")
    if generations_meta:
        lines.append("")
        lines.append("Generation metadata:")
        for k, v in generations_meta.items():
            lines.append(f"- {k}: {v}")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_analysis_pipeline(
    rating_paths: Sequence[Path],
    *,
    mapping_path: Path | None = None,
    analysis_dir: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    cfg = load_config()
    analysis_dir = analysis_dir or cfg.analysis_dir
    report_path = report_path or (repo_root() / "reports" / "pilot_report.md")

    if not rating_paths:
        path = generate_report(
            ratings=None,
            generations_meta=None,
            output_path=report_path,
        )
        return {"report": path, "ratings": 0}

    ratings = load_all_ratings(rating_paths)
    if mapping_path and mapping_path.is_file():
        mapping = _load_mapping(mapping_path)
        ratings = attach_model_from_mapping(ratings, mapping)

    paths = generate_analysis_tables(ratings, analysis_dir)
    figs = generate_figures(ratings, analysis_dir / "figures")
    report = generate_report(
        ratings=ratings,
        generations_meta={"n_ratings": len(ratings)},
        output_path=report_path,
        analysis_paths=paths,
    )
    return {"report": report, "tables": paths, "figures": figs, "ratings": len(ratings)}


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.analysis",
        description="Analyze ratings and generate pilot report/figures.",
    )
    parser.add_argument(
        "ratings",
        nargs="*",
        help="One or more filled ratings CSV files",
    )
    parser.add_argument(
        "--mapping",
        default=None,
        help="Private blind_mapping CSV to attach model IDs",
    )
    parser.add_argument(
        "--report-only-template",
        action="store_true",
        help="Write template report even without ratings",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    print(PILOT_WARNING)
    rating_paths = [Path(p) for p in args.ratings]
    if not rating_paths and not args.report_only_template:
        # default: template report
        args.report_only_template = True

    if args.report_only_template and not rating_paths:
        out = generate_report(
            ratings=None,
            generations_meta=None,
            output_path=repo_root() / "reports" / "pilot_report.md",
        )
        print(f"Wrote template report: {out}")
        sys.exit(0)

    result = run_analysis_pipeline(
        rating_paths,
        mapping_path=Path(args.mapping) if args.mapping else None,
    )
    print(f"Ratings analyzed: {result.get('ratings')}")
    print(f"Report: {result.get('report')}")
    sys.exit(0)


if __name__ == "__main__":
    main()

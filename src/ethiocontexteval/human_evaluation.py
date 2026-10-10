"""Human evaluation templates, loading, and error taxonomy helpers."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ethiocontexteval.config import load_config, repo_root

# Rating dimensions (1-5). safety may be left blank when not applicable.
RATING_DIMENSIONS = (
    "correctness",
    "context_fidelity",
    "instruction_following",
    "language_quality",
    "usefulness",
    "safety",
)

TEMPLATE_FIELDS = (
    "blind_id",
    "scenario_id",
    "language",
    "correctness",
    "context_fidelity",
    "instruction_following",
    "language_quality",
    "usefulness",
    "safety",
    "hallucination_detected",
    "error_codes",
    "evaluator_notes",
    "evaluator_id",
)

ERROR_TAXONOMY: dict[str, str] = {
    "E1": "factual error",
    "E2": "Ethiopian-context misunderstanding",
    "E3": "language misunderstanding",
    "E4": "hallucination",
    "E5": "instruction-following failure",
    "E6": "English/language leakage",
    "E7": "cultural mismatch",
    "E8": "unnecessary refusal",
    "E9": "unsafe compliance",
    "E10": "incomplete answer",
}


def create_rating_template(
    blinded_csv: Path,
    output_csv: Path,
    *,
    evaluator_id: str = "",
) -> Path:
    """Create an empty rating sheet from a blinded responses CSV."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with blinded_csv.open(encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src)
        rows_in = list(reader)

    with output_csv.open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=list(TEMPLATE_FIELDS))
        writer.writeheader()
        for row in rows_in:
            writer.writerow(
                {
                    "blind_id": row.get("blind_id", ""),
                    "scenario_id": row.get("scenario_id", ""),
                    "language": row.get("language", ""),
                    "correctness": "",
                    "context_fidelity": "",
                    "instruction_following": "",
                    "language_quality": "",
                    "usefulness": "",
                    "safety": "",
                    "hallucination_detected": "",
                    "error_codes": "",
                    "evaluator_notes": "",
                    "evaluator_id": evaluator_id,
                }
            )
    return output_csv


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"na", "n/a", "none", "null"}:
        return None
    return int(s)


def _parse_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s == "" or s in {"na", "n/a"}:
        return None
    if s in {"1", "true", "yes", "y"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean from {value!r}")


def load_ratings(path: Path | str) -> list[dict[str, Any]]:
    """Load a filled ratings CSV into normalized dict rows."""
    path = Path(path)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                item = {
                    "blind_id": (raw.get("blind_id") or "").strip(),
                    "scenario_id": (raw.get("scenario_id") or "").strip(),
                    "language": (raw.get("language") or "").strip().lower(),
                    "correctness": _parse_optional_int(raw.get("correctness")),
                    "context_fidelity": _parse_optional_int(raw.get("context_fidelity")),
                    "instruction_following": _parse_optional_int(
                        raw.get("instruction_following")
                    ),
                    "language_quality": _parse_optional_int(raw.get("language_quality")),
                    "usefulness": _parse_optional_int(raw.get("usefulness")),
                    "safety": _parse_optional_int(raw.get("safety")),
                    "hallucination_detected": _parse_optional_bool(
                        raw.get("hallucination_detected")
                    ),
                    "error_codes": _normalize_error_codes(raw.get("error_codes")),
                    "evaluator_notes": (raw.get("evaluator_notes") or "").strip(),
                    "evaluator_id": (raw.get("evaluator_id") or "").strip(),
                    "source_file": str(path),
                }
            except ValueError as exc:
                raise ValueError(f"{path} row {i}: {exc}") from exc
            for dim in RATING_DIMENSIONS:
                val = item[dim]
                if val is not None and (val < 1 or val > 5):
                    raise ValueError(f"{path} row {i}: {dim}={val} out of range 1..5")
            rows.append(item)
    return rows


def load_all_ratings(paths: Sequence[Path | str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        out.extend(load_ratings(p))
    return out


def _normalize_error_codes(value: Any) -> list[str]:
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    parts = [p.strip().upper() for p in s.replace(";", ",").split(",")]
    codes = []
    for p in parts:
        if not p:
            continue
        if p not in ERROR_TAXONOMY and not p.startswith("E"):
            # allow unknown but keep
            pass
        codes.append(p)
    return codes


def taxonomy_markdown() -> str:
    lines = ["| Code | Description |", "|------|-------------|"]
    for code, desc in ERROR_TAXONOMY.items():
        lines.append(f"| {code} | {desc} |")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.human_evaluation",
        description="Create rating templates and inspect error taxonomy.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_tmpl = sub.add_parser("template", help="Create rating CSV from blinded responses")
    p_tmpl.add_argument("blinded_csv")
    p_tmpl.add_argument(
        "--out",
        default=None,
        help="Output ratings template path",
    )
    p_tmpl.add_argument("--evaluator-id", default="")

    sub.add_parser("taxonomy", help="Print error taxonomy")

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "taxonomy":
        print(taxonomy_markdown())
        for code, desc in ERROR_TAXONOMY.items():
            print(f"{code}: {desc}")
        sys.exit(0)

    cfg = load_config()
    blinded = Path(args.blinded_csv)
    out = Path(args.out) if args.out else (
        cfg.ratings_dir / f"ratings_template_{blinded.stem}.csv"
    )
    path = create_rating_template(blinded, out, evaluator_id=args.evaluator_id)
    print(f"Wrote rating template: {path}")
    print(f"Guidelines: {repo_root() / 'docs' / 'annotation-guidelines.md'}")
    sys.exit(0)


if __name__ == "__main__":
    main()

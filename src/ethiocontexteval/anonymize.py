"""Blind model responses for human evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ethiocontexteval.config import load_config, repo_root


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def load_generations(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def anonymize_generations(
    generations: Sequence[dict[str, Any]],
    *,
    only_ok: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Create blinded rows and a private mapping.

    Blinded rows never include model_id, model_name, or provider.
    """
    blinded: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []

    # Shuffle order so model identity is not inferable from sort position.
    indexed = list(enumerate(generations))
    # Deterministic-enough shuffle keyed by response_id content via UUID reassignment only;
    # random order: sort by new blind id after assignment.
    temp: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for _, row in indexed:
        if only_ok and row.get("status") not in (None, "ok"):
            # still allow rows without status field if response present
            if row.get("status") == "error":
                continue
        response = row.get("response")
        if response is None or str(response).strip() == "":
            continue
        blind_id = f"B-{uuid.uuid4()}"
        blind_row = {
            "blind_id": blind_id,
            "scenario_id": row.get("scenario_id"),
            "domain": row.get("domain"),
            "language": row.get("language"),
            "variant": row.get("variant") or "standard",
            "run": row.get("run"),
            "response": response,
        }
        map_row = {
            "blind_id": blind_id,
            "response_id": row.get("response_id"),
            "model_id": row.get("model_id"),
            "model_name": row.get("model_name"),
            "scenario_id": row.get("scenario_id"),
            "language": row.get("language"),
            "run": row.get("run"),
        }
        temp.append((blind_row, map_row))

    temp.sort(key=lambda pair: pair[0]["blind_id"])
    for blind_row, map_row in temp:
        blinded.append(blind_row)
        mapping.append(map_row)
    return blinded, mapping


def write_blinded_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "blind_id",
        "scenario_id",
        "domain",
        "language",
        "variant",
        "run",
        "response",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def write_mapping_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "blind_id",
        "response_id",
        "model_id",
        "model_name",
        "scenario_id",
        "language",
        "run",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def anonymize_file(
    input_path: Path,
    *,
    blinded_path: Path | None = None,
    mapping_path: Path | None = None,
) -> tuple[Path, Path]:
    cfg = load_config()
    stamp = _utc_stamp()
    blinded_path = blinded_path or (cfg.blinded_dir / f"blinded_responses_{stamp}.csv")
    mapping_path = mapping_path or (cfg.raw_dir / f"blind_mapping_{stamp}.csv")

    generations = load_generations(input_path)
    blinded, mapping = anonymize_generations(generations)
    write_blinded_csv(blinded_path, blinded)
    write_mapping_csv(mapping_path, mapping)
    return blinded_path, mapping_path


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.anonymize",
        description="Create blinded response CSVs and private model mappings.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to generations JSONL (results/raw/generations_*.jsonl)",
    )
    parser.add_argument("--blinded-out", default=None)
    parser.add_argument("--mapping-out", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.input:
        raw = repo_root() / "results" / "raw"
        candidates = sorted(raw.glob("generations_*.jsonl"))
        if not candidates:
            print("No generations JSONL found. Pass input path explicitly.")
            sys.exit(1)
        input_path = candidates[-1]
        print(f"Using latest generations file: {input_path}")
    else:
        input_path = Path(args.input)

    if not input_path.is_file():
        print(f"Input not found: {input_path}")
        sys.exit(1)

    blinded_path, mapping_path = anonymize_file(
        input_path,
        blinded_path=Path(args.blinded_out) if args.blinded_out else None,
        mapping_path=Path(args.mapping_out) if args.mapping_out else None,
    )
    print(f"Blinded responses (share with evaluators): {blinded_path}")
    print(f"PRIVATE mapping (do not publish):          {mapping_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()

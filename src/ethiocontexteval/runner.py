"""Experiment runner for EthioContextEval pilot generations."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ethiocontexteval.bedrock_client import BedrockClient
from ethiocontexteval.config import PilotConfig, load_config
from ethiocontexteval.dataset import (
    DatasetValidationError,
    Scenario,
    executable_scenarios,
    load_scenarios,
)


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def plan_requests(
    scenarios: Sequence[Scenario],
    cfg: PilotConfig,
) -> list[dict[str, Any]]:
    """Build the cartesian product of executable scenarios x models x runs."""
    exe = executable_scenarios(scenarios)
    models = cfg.enabled_models()
    jobs: list[dict[str, Any]] = []
    for sc in exe:
        for model in models:
            for run in range(1, cfg.runs + 1):
                jobs.append(
                    {
                        "scenario_id": sc.scenario_id,
                        "domain": sc.domain,
                        "language": sc.language,
                        "variant": sc.variant,
                        "model_name": model.name,
                        "model_id": model.model_id,
                        "run": run,
                        "prompt": sc.prompt,
                    }
                )
    return jobs


def dry_run_report(cfg: PilotConfig, dataset_path: Path | None = None) -> dict[str, Any]:
    """Validate data and report planned API usage without calling Bedrock."""
    path = dataset_path or cfg.dataset_path
    scenarios = load_scenarios(path, strict=True)
    exe = executable_scenarios(scenarios)
    jobs = plan_requests(scenarios, cfg)
    models = cfg.enabled_models()

    by_lang: dict[str, int] = {}
    for s in exe:
        by_lang[s.language] = by_lang.get(s.language, 0) + 1

    report = {
        "dataset": str(path),
        "total_records": len(scenarios),
        "executable_records": len(exe),
        "executable_by_language": by_lang,
        "enabled_models": [{"name": m.name, "model_id": m.model_id} for m in models],
        "runs_per_cell": cfg.runs,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "aws_region": cfg.aws_region,
        "expected_api_requests": len(jobs),
        "formula": (
            f"{len(exe)} executable scenarios × {len(models)} models × {cfg.runs} runs "
            f"= {len(jobs)} requests"
        ),
    }
    return report


def _print_dry_run(report: dict[str, Any]) -> None:
    print("=== EthioContextEval dry run (no Bedrock calls) ===")
    print(f"Dataset:              {report['dataset']}")
    print(f"Total records:        {report['total_records']}")
    print(f"Executable records:   {report['executable_records']}")
    print(f"Executable by lang:   {report['executable_by_language']}")
    print(f"Enabled models:       {report['enabled_models']}")
    print(f"Runs per cell:        {report['runs_per_cell']}")
    print(f"Temperature:          {report['temperature']}")
    print(f"Max tokens:           {report['max_tokens']}")
    print(f"AWS region:           {report['aws_region']}")
    print(f"Expected API calls:   {report['expected_api_requests']}")
    print(f"Plan:                 {report['formula']}")
    print("Bedrock was NOT invoked.")


def _result_key(row: dict[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        str(row.get("scenario_id")),
        str(row.get("language")),
        str(row.get("variant") or "standard"),
        str(row.get("model_id")),
        int(row.get("run") or 0),
    )


def _load_completed_keys(path: Path) -> set[tuple[str, str, str, str, int]]:
    done: set[tuple[str, str, str, str, int]] = set()
    if not path.is_file():
        return done
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") == "ok":
                done.add(_result_key(row))
    return done


def run_experiment(
    cfg: PilotConfig,
    *,
    dataset_path: Path | None = None,
    output_path: Path | None = None,
    resume_from: Path | None = None,
    verify_models: bool = True,
    client: BedrockClient | None = None,
) -> Path:
    """
    Execute planned generations and write JSONL incrementally.

    Failures are logged as rows with status=error; the run continues.
    """
    path = dataset_path or cfg.dataset_path
    scenarios = load_scenarios(path, strict=True)
    jobs = plan_requests(scenarios, cfg)
    if not jobs:
        raise RuntimeError("No executable jobs planned. Check dataset translation status.")

    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    out = output_path or (cfg.raw_dir / f"generations_{_utc_stamp()}.jsonl")
    if resume_from and resume_from.is_file() and resume_from != out:
        # seed output with prior completed rows
        out.write_text(resume_from.read_text(encoding="utf-8"), encoding="utf-8")
    completed = _load_completed_keys(out)

    bedrock = client or BedrockClient(region_name=cfg.aws_region)
    if verify_models:
        for m in cfg.enabled_models():
            bedrock.ensure_model_available(m.model_id)

    scenario_map = {(s.scenario_id, s.language, s.variant): s for s in scenarios}

    print(f"Writing results to {out}")
    print(f"Planned jobs: {len(jobs)}; already completed: {len(completed)}")

    with out.open("a", encoding="utf-8") as sink:
        for job in jobs:
            key = (
                job["scenario_id"],
                job["language"],
                job["variant"],
                job["model_id"],
                job["run"],
            )
            if key in completed:
                continue

            sc = scenario_map.get((job["scenario_id"], job["language"], job["variant"]))
            prompt = job["prompt"] or (sc.prompt if sc else None)
            response_id = str(uuid.uuid4())
            row: dict[str, Any] = {
                "response_id": response_id,
                "scenario_id": job["scenario_id"],
                "domain": job["domain"],
                "language": job["language"],
                "variant": job["variant"],
                "model_id": job["model_id"],
                "model_name": job["model_name"],
                "run": job["run"],
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "prompt": prompt,
                "response": None,
                "latency_seconds": None,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": None,
                "status": "error",
            }

            if not prompt:
                row["error"] = "empty prompt"
                sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                sink.flush()
                continue

            result = bedrock.converse(
                model_id=job["model_id"],
                prompt=str(prompt),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
            )
            row.update(
                {
                    "response": result.response_text,
                    "latency_seconds": result.latency_seconds,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "total_tokens": result.total_tokens,
                    "timestamp": result.timestamp,
                    "error": result.error,
                    "status": result.status,
                    "stop_reason": result.raw_stop_reason,
                }
            )
            sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            sink.flush()
            status_icon = "OK" if result.status == "ok" else "ERR"
            print(
                f"[{status_icon}] {job['scenario_id']} {job['language']} "
                f"{job['model_name']} run={job['run']}"
            )

    return out


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.runner",
        description="Run EthioContextEval pilot generations on Amazon Bedrock.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to scenarios JSONL (default from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and plan only; do not call Bedrock",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute paid Bedrock calls (requires explicit flag)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL path for generations",
    )
    parser.add_argument(
        "--resume-from",
        default=None,
        help="Prior generations JSONL to skip completed ok rows",
    )
    parser.add_argument(
        "--skip-model-check",
        action="store_true",
        help="Do not pre-check model availability",
    )
    parser.add_argument("--region", default=None, help="Override AWS region")
    parser.add_argument("--runs", type=int, default=None, help="Override repeated runs")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = load_config(dataset_path=args.dataset)
    if args.region:
        cfg.aws_region = args.region
    if args.runs is not None:
        cfg.runs = args.runs
    if args.max_tokens is not None:
        cfg.max_tokens = args.max_tokens
    if args.temperature is not None:
        cfg.temperature = args.temperature
    if args.dataset:
        cfg.dataset_path = Path(args.dataset)

    try:
        if args.dry_run or not args.execute:
            if not args.dry_run and not args.execute:
                print(
                    "Neither --dry-run nor --execute specified. "
                    "Defaulting to --dry-run for safety."
                )
            report = dry_run_report(cfg, dataset_path=cfg.dataset_path)
            _print_dry_run(report)
            sys.exit(0)

        # explicit execute
        out = run_experiment(
            cfg,
            dataset_path=cfg.dataset_path,
            output_path=Path(args.output) if args.output else None,
            resume_from=Path(args.resume_from) if args.resume_from else None,
            verify_models=not args.skip_model_check,
        )
        print(f"Done. Results: {out}")
        sys.exit(0)
    except DatasetValidationError as exc:
        print(exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Provider-independent experiment runner for EthioContextEval pilot generations."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ethiocontexteval.config import PilotConfig, load_config
from ethiocontexteval.dataset import (
    DatasetValidationError,
    Scenario,
    executable_scenarios,
    load_scenarios,
)
from ethiocontexteval.providers import ModelProvider, ProviderError, get_provider


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


def _language_skip_summary(scenarios: Sequence[Scenario]) -> dict[str, Any]:
    by_lang: dict[str, list[Scenario]] = {}
    for s in scenarios:
        by_lang.setdefault(s.language, []).append(s)

    executable_langs: list[str] = []
    skipped: dict[str, str] = {}
    lang_names = {"en": "English", "am": "Amharic", "om": "Afaan Oromo"}
    for lang, rows in sorted(by_lang.items()):
        exe = [r for r in rows if r.is_executable()]
        label = lang_names.get(lang, lang)
        if exe:
            executable_langs.append(label)
        else:
            statuses = sorted({(r.translation_status or "unknown") for r in rows})
            skipped[label] = ", ".join(statuses) if statuses else "not executable"
    return {"executable_languages": executable_langs, "skipped": skipped}


def dry_run_report(
    cfg: PilotConfig,
    dataset_path: Path | None = None,
    *,
    provider: ModelProvider | None = None,
    check_models: bool = True,
) -> dict[str, Any]:
    """Validate data and report planned generations without inference."""
    path = dataset_path or cfg.dataset_path
    scenarios = load_scenarios(path, strict=True)
    exe = executable_scenarios(scenarios)
    jobs = plan_requests(scenarios, cfg)
    models = cfg.enabled_models()
    lang_summary = _language_skip_summary(scenarios)

    by_lang: dict[str, int] = {}
    for s in exe:
        by_lang[s.language] = by_lang.get(s.language, 0) + 1

    model_status: list[dict[str, Any]] = []
    provider_health: dict[str, Any] | None = None
    if provider is not None:
        provider_health = provider.health_check()
        if check_models:
            available_ids = {m.model_id for m in provider.list_models()} if provider_health.get("ok") else set()
            for m in models:
                entry: dict[str, Any] = {
                    "name": m.name,
                    "model_id": m.model_id,
                    "available": None,
                    "note": None,
                }
                if not provider_health.get("ok"):
                    entry["available"] = False
                    entry["note"] = provider_health.get("message")
                else:
                    try:
                        provider.ensure_model_available(m.model_id)
                        entry["available"] = True
                    except ProviderError as exc:
                        entry["available"] = False
                        entry["note"] = str(exc)
                    # also surface raw membership
                    if m.model_id not in available_ids and entry["available"]:
                        entry["note"] = entry.get("note") or "matched via prefix/alias"
                model_status.append(entry)

    report = {
        "provider": cfg.provider,
        "dataset": str(path),
        "total_records": len(scenarios),
        "executable_records": len(exe),
        "executable_by_language": by_lang,
        "executable_languages": lang_summary["executable_languages"],
        "skipped": lang_summary["skipped"],
        "enabled_models": [{"name": m.name, "model_id": m.model_id} for m in models],
        "model_status": model_status,
        "provider_health": provider_health,
        "runs_per_cell": cfg.runs,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "aws_region": cfg.aws_region if cfg.provider == "bedrock" else None,
        "ollama_base_url": cfg.ollama_base_url if cfg.provider == "ollama" else None,
        "expected_generations": len(jobs),
        "formula": (
            f"{len(exe)} executable scenarios x {len(models)} models x {cfg.runs} runs "
            f"= {len(jobs)} generations"
        ),
    }
    return report


def _print_dry_run(report: dict[str, Any]) -> None:
    print("=== EthioContextEval dry run (no model inference) ===")
    print(f"Provider:             {report['provider']}")
    print(f"Dataset:              {report['dataset']}")
    print(f"Total records:        {report['total_records']}")
    print(f"Executable records:   {report['executable_records']}")
    print(f"Executable languages: {report['executable_languages']}")
    skipped = report.get("skipped") or {}
    if skipped:
        print("Skipped:")
        for lang, reason in skipped.items():
            print(f"  - {lang}: {reason}")
    print(f"Enabled models:       {report['enabled_models']}")
    if report.get("model_status"):
        print("Model availability:")
        for m in report["model_status"]:
            flag = "available" if m.get("available") else "MISSING/unavailable"
            extra = f" ({m['note']})" if m.get("note") else ""
            print(f"  - {m['name']}: {m['model_id']} -> {flag}{extra}")
    if report.get("provider_health"):
        ph = report["provider_health"]
        print(f"Provider health:      ok={ph.get('ok')} — {ph.get('message')}")
    print(f"Runs per cell:        {report['runs_per_cell']}")
    print(f"Temperature:          {report['temperature']}")
    print(f"Max tokens:           {report['max_tokens']}")
    if report.get("ollama_base_url"):
        print(f"Ollama base URL:      {report['ollama_base_url']}")
    if report.get("aws_region"):
        print(f"AWS region:           {report['aws_region']}")
    print(f"Expected generations: {report['expected_generations']}")
    print(f"Plan:                 {report['formula']}")
    print("No inference requests were sent.")


def _result_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, int]:
    return (
        str(row.get("provider") or ""),
        str(row.get("scenario_id")),
        str(row.get("language")),
        str(row.get("variant") or "standard"),
        str(row.get("model_id")),
        int(row.get("run") or 0),
    )


def _load_completed_keys(path: Path) -> set[tuple[str, str, str, str, str, int]]:
    done: set[tuple[str, str, str, str, str, int]] = set()
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


def create_provider_from_config(cfg: PilotConfig) -> ModelProvider:
    return get_provider(
        cfg.provider,
        region=cfg.aws_region,
        base_url=cfg.ollama_base_url,
    )


def run_experiment(
    cfg: PilotConfig,
    *,
    dataset_path: Path | None = None,
    output_path: Path | None = None,
    resume_from: Path | None = None,
    verify_models: bool = True,
    provider: ModelProvider | None = None,
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

    backend = provider or create_provider_from_config(cfg)
    health = backend.health_check()
    if not health.get("ok"):
        raise ProviderError(
            f"Provider '{backend.provider_name()}' health check failed: {health.get('message')}"
        )

    if verify_models:
        for m in cfg.enabled_models():
            backend.ensure_model_available(m.model_id)

    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    out = output_path or (cfg.raw_dir / f"generations_{_utc_stamp()}.jsonl")
    if resume_from and resume_from.is_file() and resume_from != out:
        out.write_text(resume_from.read_text(encoding="utf-8"), encoding="utf-8")
    completed = _load_completed_keys(out)

    scenario_map = {(s.scenario_id, s.language, s.variant): s for s in scenarios}

    print(f"Provider: {backend.provider_name()}")
    print(f"Writing results to {out}")
    print(f"Planned jobs: {len(jobs)}; already completed: {len(completed)}")

    with out.open("a", encoding="utf-8") as sink:
        for job in jobs:
            key = (
                backend.provider_name(),
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
                "provider": backend.provider_name(),
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
                "finish_reason": None,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": None,
                "status": "error",
                "provider_metadata": {},
            }

            if not prompt:
                row["error"] = "empty prompt"
                sink.write(json.dumps(row, ensure_ascii=False) + "\n")
                sink.flush()
                continue

            result = backend.generate(
                model_id=job["model_id"],
                prompt=str(prompt),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
            )
            row.update(
                {
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "response": result.response,
                    "latency_seconds": result.latency_seconds,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "total_tokens": result.total_tokens,
                    "finish_reason": result.finish_reason,
                    "timestamp": result.timestamp,
                    "error": result.error,
                    "status": result.status,
                    "provider_metadata": result.provider_metadata,
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
        description="Run EthioContextEval pilot generations (provider-independent).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=["mock", "ollama", "bedrock"],
        help="Inference provider (default from config / ETHIOEVAL_PROVIDER / ollama)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to models JSON (e.g. config/models.local.json)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to scenarios JSONL (default from config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and plan only; do not call any model",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute model inference (requires explicit flag)",
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
    parser.add_argument("--region", default=None, help="AWS region (bedrock only)")
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="Ollama base URL (default http://localhost:11434)",
    )
    parser.add_argument("--runs", type=int, default=None, help="Override repeated runs")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = load_config(
        dataset_path=args.dataset,
        models_config_path=args.config,
        provider=args.provider,
    )
    if args.region:
        cfg.aws_region = args.region
    if args.ollama_url:
        cfg.ollama_base_url = args.ollama_url
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
            backend = None
            # For dry-run, try to attach provider health when possible (mock always works)
            try:
                backend = create_provider_from_config(cfg)
            except ProviderError as exc:
                print(f"Provider init note: {exc}")
            report = dry_run_report(
                cfg,
                dataset_path=cfg.dataset_path,
                provider=backend,
                check_models=backend is not None and not args.skip_model_check,
            )
            _print_dry_run(report)
            sys.exit(0)

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
    except ProviderError as exc:
        print(f"PROVIDER ERROR: {exc}")
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

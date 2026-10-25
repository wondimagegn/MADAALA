"""Provider-independent experiment runner for MADAALA pilot generations."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from madaala.config import PilotConfig, load_config
from madaala.dataset import (
    DatasetValidationError,
    Scenario,
    executable_scenarios,
    is_research_grade,
    load_scenarios,
)
from madaala.providers import ModelProvider, ProviderError, get_provider


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def filter_scenarios(
    scenarios: Sequence[Scenario],
    *,
    scenario_id: str | None = None,
    language: str | None = None,
) -> list[Scenario]:
    """Optionally filter loaded records by scenario_id and/or language."""
    rows = list(scenarios)
    if scenario_id is not None:
        rows = [s for s in rows if s.scenario_id == scenario_id]
        if not rows:
            raise ValueError(f"Scenario not found: {scenario_id}")
    if language is not None:
        rows = [s for s in rows if s.language == language]
        if not rows:
            raise ValueError(f"No records found for language: {language}")
    return rows


def select_models(cfg: PilotConfig, model_id: str | None = None) -> list:
    """Return enabled models, optionally restricted to a single model_id."""
    models = cfg.enabled_models()
    if model_id is None:
        return models
    matched = [m for m in models if m.model_id == model_id]
    if not matched:
        all_ids = {m.model_id: m for m in cfg.models}
        if model_id in all_ids and not all_ids[model_id].enabled:
            raise ValueError(f"Model is disabled: {model_id}")
        raise ValueError(f"Model not found or not enabled: {model_id}")
    return matched


def plan_requests(
    scenarios: Sequence[Scenario],
    cfg: PilotConfig,
    *,
    models: Sequence | None = None,
) -> list[dict[str, Any]]:
    """Build the cartesian product of executable scenarios x models x runs."""
    exe = executable_scenarios(scenarios, allow_unvalidated=cfg.allow_unvalidated)
    models = list(models) if models is not None else cfg.enabled_models()
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


def _language_skip_summary(
    scenarios: Sequence[Scenario],
    *,
    allow_unvalidated: bool = False,
) -> dict[str, Any]:
    by_lang: dict[str, list[Scenario]] = {}
    for s in scenarios:
        by_lang.setdefault(s.language, []).append(s)

    executable_langs: list[str] = []
    skipped: dict[str, str] = {}
    lang_names = {"en": "English", "am": "Amharic", "om": "Afaan Oromo"}
    for lang, rows in sorted(by_lang.items()):
        exe = executable_scenarios(rows, allow_unvalidated=allow_unvalidated)
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
    scenario_id: str | None = None,
    language: str | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Validate dataset + config and report planned generations without inference."""
    path = dataset_path or cfg.dataset_path
    scenarios = load_scenarios(path, strict=True)
    scenarios = filter_scenarios(scenarios, scenario_id=scenario_id, language=language)
    models = select_models(cfg, model_id)
    exe = executable_scenarios(scenarios, allow_unvalidated=cfg.allow_unvalidated)
    jobs = plan_requests(scenarios, cfg, models=models)
    lang_summary = _language_skip_summary(scenarios, allow_unvalidated=cfg.allow_unvalidated)

    by_lang: dict[str, int] = {}
    for s in exe:
        by_lang[s.language] = by_lang.get(s.language, 0) + 1

    model_status: list[dict[str, Any]] = []
    provider_health: dict[str, Any] | None = None
    if provider is not None:
        provider_health = provider.health_check()
        if check_models:
            for m in models:
                entry: dict[str, Any] = {
                    "name": m.name,
                    "model_id": m.model_id,
                    "available": None,
                    "note": None,
                }
                try:
                    entry["available"] = bool(provider.is_model_available(m.model_id))
                except ProviderError as exc:
                    entry["available"] = False
                    entry["note"] = str(exc)
                except Exception as exc:  # noqa: BLE001
                    entry["available"] = False
                    entry["note"] = f"check failed: {exc}"
                model_status.append(entry)

    report = {
        "provider": cfg.provider,
        "dataset": str(path),
        "total_records": len(scenarios),
        "executable_records": len(exe),
        "executable_by_language": by_lang,
        "executable_languages": lang_summary["executable_languages"],
        "skipped": lang_summary["skipped"],
        "selected_records": len(exe),
        "selected_models": len(models),
        "enabled_models": [{"name": m.name, "model_id": m.model_id} for m in models],
        "model_status": model_status,
        "provider_health": provider_health,
        "runs_per_cell": cfg.runs,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "expected_generations": len(jobs),
        "allow_unvalidated": cfg.allow_unvalidated,
        "aws_region": cfg.aws_region if cfg.provider == "bedrock" else None,
        "aws_profile": cfg.aws_profile if cfg.provider == "bedrock" else None,
        "formula": (
            f"{len(exe)} executable records Ã— {len(models)} models Ã— "
            f"{cfg.runs} runs = {len(jobs)}"
        ),
    }
    return report


def _print_dry_run(report: dict[str, Any]) -> None:
    print("=== MADAALA dry run ===")
    for label, key in [
        ("Provider", "provider"),
        ("AWS profile", "aws_profile"),
        ("AWS region", "aws_region"),
        ("Dataset", "dataset"),
        ("Selected records", "selected_records"),
        ("Selected models", "selected_models"),
        ("Runs", "runs_per_cell"),
        ("Temperature", "temperature"),
        ("Max tokens", "max_tokens"),
        ("Expected generations", "expected_generations"),
    ]:
        if report.get(key) is not None:
            print(f"{label + ':':23} {report[key]}")
    if report.get("skipped"):
        print(f"Skipped: {report['skipped']}")
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
    """Instantiate the configured provider backend."""
    kwargs: dict[str, Any] = {
        "region": cfg.aws_region,
    }
    if cfg.provider == "bedrock" and cfg.aws_profile:
        kwargs["profile"] = cfg.aws_profile
    return get_provider(cfg.provider, **kwargs)


def run_experiment(
    cfg: PilotConfig,
    *,
    dataset_path: Path | None = None,
    output_path: Path | None = None,
    resume_from: Path | None = None,
    verify_models: bool = True,
    provider: ModelProvider | None = None,
    scenario_id: str | None = None,
    language: str | None = None,
    model_id: str | None = None,
) -> Path:
    """
    Execute planned generations and write JSONL incrementally.

    Failures are logged as rows with status=error; the run continues.
    """
    path = dataset_path or cfg.dataset_path
    scenarios = load_scenarios(path, strict=True)
    scenarios = filter_scenarios(scenarios, scenario_id=scenario_id, language=language)
    models = select_models(cfg, model_id)
    jobs = plan_requests(scenarios, cfg, models=models)
    if not jobs:
        raise RuntimeError("No executable jobs planned. Check dataset translation status.")

    backend = provider or create_provider_from_config(cfg)
    health = backend.health_check()
    if not health.get("ok"):
        raise ProviderError(
            f"Provider '{backend.provider_name()}' health check failed: {health.get('message')}"
        )

    if verify_models:
        for m in models:
            backend.ensure_model_available(m.model_id)

    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    out = output_path or (cfg.raw_dir / f"generations_{_utc_stamp()}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if resume_from and not resume_from.is_file():
        raise FileNotFoundError(f"Resume file not found: {resume_from}")
    if resume_from and resume_from.is_file() and resume_from != out:
        out.write_text(resume_from.read_text(encoding="utf-8"), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
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
            research = is_research_grade(sc) if sc is not None else False
            technical = not research
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
                "validation_status": sc.validation_status if sc else None,
                "validation_status_at_run": sc.validation_status if sc else None,
                "translation_status_at_run": sc.translation_status if sc else None,
                "research_grade": research,
                "technical_pilot": technical,
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

            try:
                result = backend.generate(
                    model_id=job["model_id"],
                    prompt=str(prompt),
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                )
            except Exception as exc:
                from madaala.providers import GenerationResult

                result = GenerationResult(
                    provider=backend.provider_name(),
                    model_id=job["model_id"],
                    response=None,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
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
        prog="python -m madaala.runner",
        description="Run MADAALA pilot generations (provider-independent).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=["mock", "bedrock"],
        help="Inference provider (default from config / MADAALA_PROVIDER / bedrock)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to models JSON (e.g. config/models.bedrock.json)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to scenarios JSONL (default from config)",
    )
    parser.add_argument(
        "--profile",
        help="AWS profile name for Bedrock authentication",
    )
    parser.add_argument(
        "--scenario",
        help="Run only the specified scenario_id",
    )
    parser.add_argument(
        "--language",
        choices=["en", "am", "om"],
        help="Run only the specified language",
    )
    parser.add_argument(
        "--model",
        help="Run only the specified configured model_id",
    )
    parser.add_argument(
        "--allow-unvalidated",
        action="store_true",
        help="Allow pending/unvalidated language records for technical-pilot execution",
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
    parser.add_argument("--runs", type=int, default=None, help="Override repeated runs")
    parser.add_argument(
        "--max-tokens", type=int, default=None, help="Maximum output tokens per generation"
    )
    parser.add_argument(
        "--temperature", type=float, default=None, help="Sampling temperature (0 to 1)"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        return _run_cli(args, parser)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


def _run_cli(args, parser) -> None:
    cfg = load_config(
        dataset_path=args.dataset,
        models_config_path=args.config,
        provider=args.provider,
    )
    if args.region:
        cfg.aws_region = args.region
    if args.profile:
        cfg.aws_profile = args.profile
    if args.allow_unvalidated:
        cfg.allow_unvalidated = True
    if args.runs is not None:
        cfg.runs = args.runs
    if args.max_tokens is not None:
        cfg.max_tokens = args.max_tokens
    if args.temperature is not None:
        cfg.temperature = args.temperature
    if args.dataset:
        cfg.dataset_path = Path(args.dataset)

    if cfg.runs < 1 or cfg.max_tokens < 1 or not 0 <= cfg.temperature <= 1:
        parser.error("runs and max-tokens must be positive; temperature must be in [0, 1]")
    if args.dry_run and args.execute:
        parser.error("Choose either --dry-run or --execute")
    if not cfg.enabled_models():
        parser.error("No enabled models in configuration")
    if cfg.allow_unvalidated:
        print(
            "WARNING: Unvalidated language data are being used. These outputs are technical-pilot results only and must not be presented as expert-validated research findings."
        )
    try:
        if args.dry_run or not args.execute:
            if not args.dry_run and not args.execute:
                print(
                    "Neither --dry-run nor --execute specified. Defaulting to --dry-run for safety."
                )
            backend = None  # Offline planning never initializes an AWS session.
            report = dry_run_report(
                cfg,
                dataset_path=cfg.dataset_path,
                provider=backend,
                check_models=backend is not None and not args.skip_model_check,
                scenario_id=args.scenario,
                language=args.language,
                model_id=args.model,
            )
            _print_dry_run(report)
            sys.exit(0)

        out = run_experiment(
            cfg,
            dataset_path=cfg.dataset_path,
            output_path=Path(args.output) if args.output else None,
            resume_from=Path(args.resume_from) if args.resume_from else None,
            verify_models=not args.skip_model_check,
            scenario_id=args.scenario,
            language=args.language,
            model_id=args.model,
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

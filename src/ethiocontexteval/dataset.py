"""Dataset loading and validation for EthioContextEval scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ethiocontexteval.config import (
    DOMAIN_ALIASES,
    SUPPORTED_DOMAINS,
    SUPPORTED_LANGUAGES,
    repo_root,
)

REQUIRED_FIELDS = (
    "scenario_id",
    "domain",
    "difficulty",
    "language",
    "variant",
    "prompt",
    "expected_behavior",
    "cultural_dependency",
    "safety_sensitive",
    "translation_status",
    "validation_status",
)

# Statuses that mean the prompt is not ready for model execution
NON_EXECUTABLE_TRANSLATION = {
    "pending_human_translation",
    "pending_translation",
    "untranslated",
    "master_english_only",
    "awaiting_translation",
}

EXECUTABLE_TRANSLATION = {
    "master_english",
    "human_translated",
    "expert_validated",
    "validated",
}


class DatasetValidationError(ValueError):
    """Raised when one or more scenario records fail validation."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        msg = f"Dataset validation failed with {len(self.errors)} error(s):\n" + "\n".join(
            f"  - {e}" for e in self.errors
        )
        super().__init__(msg)


@dataclass
class Scenario:
    """A single evaluation scenario record."""

    scenario_id: str
    domain: str
    difficulty: int
    language: str
    variant: str
    prompt: str | None
    expected_behavior: list[str]
    cultural_dependency: bool
    safety_sensitive: bool
    translation_status: str
    validation_status: str
    source_language: str = "en"
    linguistic_validator: str | None = None
    cultural_validator: str | None = None
    validation_notes: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.scenario_id, self.language, self.variant)

    def is_executable(self) -> bool:
        """Return True if this record may be sent to a model."""
        if self.language not in SUPPORTED_LANGUAGES:
            return False
        if self.prompt is None:
            return False
        if not str(self.prompt).strip():
            return False
        status = (self.translation_status or "").strip().lower()
        if status in NON_EXECUTABLE_TRANSLATION:
            return False
        if status.startswith("pending"):
            return False
        return status in EXECUTABLE_TRANSLATION

    def to_dict(self) -> dict[str, Any]:
        base = {
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "language": self.language,
            "variant": self.variant,
            "prompt": self.prompt,
            "expected_behavior": list(self.expected_behavior),
            "cultural_dependency": self.cultural_dependency,
            "safety_sensitive": self.safety_sensitive,
            "translation_status": self.translation_status,
            "validation_status": self.validation_status,
            "source_language": self.source_language,
            "linguistic_validator": self.linguistic_validator,
            "cultural_validator": self.cultural_validator,
            "validation_notes": self.validation_notes,
        }
        base.update(self.extra)
        return base


def normalize_domain(domain: str) -> str:
    key = (domain or "").strip().lower().replace(" ", "_")
    if key in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[key]
    if key in SUPPORTED_DOMAINS:
        return key
    return key


def _parse_bool(value: Any, field_name: str, line_no: int) -> bool | str:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return f"line {line_no}: '{field_name}' must be a boolean"


def scenario_from_dict(data: dict[str, Any], line_no: int = 0) -> tuple[Scenario | None, list[str]]:
    """Parse and lightly validate a single JSON object into a Scenario."""
    errors: list[str] = []
    loc = f"line {line_no}" if line_no else "record"

    for req in REQUIRED_FIELDS:
        if req not in data:
            errors.append(f"{loc}: missing required field '{req}'")

    if errors:
        return None, errors

    language = str(data.get("language", "")).strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        errors.append(
            f"{loc}: unsupported language '{language}' (allowed: {', '.join(SUPPORTED_LANGUAGES)})"
        )

    domain_raw = str(data.get("domain", ""))
    domain = normalize_domain(domain_raw)
    if domain not in SUPPORTED_DOMAINS:
        errors.append(
            f"{loc}: unsupported domain '{domain_raw}' (allowed: {', '.join(SUPPORTED_DOMAINS)})"
        )

    try:
        difficulty = int(data["difficulty"])
        if difficulty < 1 or difficulty > 5:
            errors.append(f"{loc}: difficulty must be in 1..5, got {difficulty}")
    except (TypeError, ValueError):
        errors.append(f"{loc}: difficulty must be an integer")
        difficulty = -1

    expected = data.get("expected_behavior")
    if not isinstance(expected, list) or not expected:
        errors.append(f"{loc}: expected_behavior must be a nonempty list")
        expected_list: list[str] = []
    else:
        expected_list = [str(x) for x in expected]
        if any(not x.strip() for x in expected_list):
            errors.append(f"{loc}: expected_behavior entries must be nonempty strings")

    cultural = _parse_bool(data.get("cultural_dependency"), "cultural_dependency", line_no)
    if isinstance(cultural, str):
        errors.append(cultural)
        cultural = False
    safety = _parse_bool(data.get("safety_sensitive"), "safety_sensitive", line_no)
    if isinstance(safety, str):
        errors.append(safety)
        safety = False

    prompt = data.get("prompt")
    if prompt is not None:
        prompt = str(prompt)
        if prompt.strip() == "":
            prompt = None

    translation_status = str(data.get("translation_status", "")).strip()
    validation_status = str(data.get("validation_status", "")).strip()
    if not translation_status:
        errors.append(f"{loc}: translation_status must be nonempty")
    if not validation_status:
        errors.append(f"{loc}: validation_status must be nonempty")

    scenario_id = str(data.get("scenario_id", "")).strip()
    if not scenario_id:
        errors.append(f"{loc}: scenario_id must be nonempty")

    variant = str(data.get("variant", "standard")).strip() or "standard"

    known = set(REQUIRED_FIELDS) | {
        "source_language",
        "linguistic_validator",
        "cultural_validator",
        "validation_notes",
    }
    extra = {k: v for k, v in data.items() if k not in known}

    if errors:
        return None, errors

    scenario = Scenario(
        scenario_id=scenario_id,
        domain=domain,
        difficulty=difficulty,
        language=language,
        variant=variant,
        prompt=prompt,
        expected_behavior=expected_list,
        cultural_dependency=bool(cultural),
        safety_sensitive=bool(safety),
        translation_status=translation_status,
        validation_status=validation_status,
        source_language=str(data.get("source_language", "en")),
        linguistic_validator=data.get("linguistic_validator"),
        cultural_validator=data.get("cultural_validator"),
        validation_notes=data.get("validation_notes"),
        extra=extra,
    )
    return scenario, []


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """Load JSONL file into a list of dicts (no semantic validation)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise DatasetValidationError([f"line {line_no}: invalid JSON ({exc})"]) from exc
            if not isinstance(obj, dict):
                raise DatasetValidationError([f"line {line_no}: each record must be a JSON object"])
            rows.append(obj)
    return rows


def load_scenarios(path: Path | str, *, strict: bool = True) -> list[Scenario]:
    """Load and validate scenarios from JSONL."""
    path = Path(path)
    raw_rows = load_jsonl(path)
    scenarios: list[Scenario] = []
    errors: list[str] = []
    seen: dict[tuple[str, str, str], int] = {}

    for line_no, row in enumerate(raw_rows, start=1):
        scenario, row_errors = scenario_from_dict(row, line_no=line_no)
        errors.extend(row_errors)
        if scenario is None:
            continue
        if scenario.key in seen:
            errors.append(
                f"line {line_no}: duplicate scenario/language/variant "
                f"{scenario.key} (first seen at logical row {seen[scenario.key]})"
            )
        else:
            seen[scenario.key] = line_no
            scenarios.append(scenario)

    if strict and errors:
        raise DatasetValidationError(errors)
    if not strict and errors:
        # still raise if structural failures left us with nothing useful
        pass
    if strict and not scenarios and not errors:
        raise DatasetValidationError(["dataset contains no scenario records"])
    if errors and not scenarios:
        raise DatasetValidationError(errors)
    return scenarios


def validate_dataset(path: Path | str) -> list[str]:
    """
    Validate dataset file.

    Returns a list of error strings (empty if valid).
    """
    path = Path(path)
    try:
        load_scenarios(path, strict=True)
    except DatasetValidationError as exc:
        return list(exc.errors)
    except FileNotFoundError as exc:
        return [str(exc)]
    return []


def is_research_grade(scenario: Scenario) -> bool:
    """True when the record is normally executable (research-path ready)."""
    return scenario.is_executable() and scenario.validation_status.strip().lower() in {
        "validated",
        "expert_validated",
    }


def _technical_pilot_eligible(scenario: Scenario) -> bool:
    """Whether a non-research-grade row may run under --allow-unvalidated."""
    if scenario.language not in SUPPORTED_LANGUAGES:
        return False
    if scenario.prompt is None or not str(scenario.prompt).strip():
        return False
    # Still block empty / missing prompts; allow pending translation statuses.
    return True


def executable_scenarios(
    scenarios: Iterable[Scenario],
    *,
    allow_unvalidated: bool = False,
) -> list[Scenario]:
    """Filter to records that may be sent to models.

    By default only research-path executable rows are included.
    With allow_unvalidated=True, pending/unvalidated language rows that still
    have a non-empty prompt are included for technical-pilot execution.
    """
    out: list[Scenario] = []
    for s in scenarios:
        if s.is_executable():
            out.append(s)
            continue
        if allow_unvalidated and _technical_pilot_eligible(s):
            out.append(s)
    return out


def iter_scenario_summaries(scenarios: Sequence[Scenario]) -> Iterator[dict[str, Any]]:
    for s in scenarios:
        yield {
            "scenario_id": s.scenario_id,
            "language": s.language,
            "domain": s.domain,
            "variant": s.variant,
            "translation_status": s.translation_status,
            "executable": s.is_executable(),
        }


def validate_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.dataset",
        description="Validate EthioContextEval scenario JSONL datasets.",
    )
    parser.add_argument(
        "command",
        choices=["validate", "summary"],
        help="validate: full checks; summary: counts and executability",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(repo_root() / "data" / "scenarios.jsonl"),
        help="Path to JSONL dataset",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    path = Path(args.path)
    if args.command == "validate":
        errors = validate_dataset(path)
        if errors:
            print(f"INVALID: {path}")
            for err in errors:
                print(f"  - {err}")
            return 1
        scenarios = load_scenarios(path, strict=True)
        exe = executable_scenarios(scenarios)
        print(f"VALID: {path}")
        print(f"  records: {len(scenarios)}")
        print(f"  executable: {len(exe)}")
        print(f"  pending/non-executable: {len(scenarios) - len(exe)}")
        return 0

    # summary
    try:
        scenarios = load_scenarios(path, strict=True)
    except (DatasetValidationError, FileNotFoundError) as exc:
        print(f"INVALID: {exc}")
        return 1
    by_lang: dict[str, int] = {}
    exe_by_lang: dict[str, int] = {}
    for s in scenarios:
        by_lang[s.language] = by_lang.get(s.language, 0) + 1
        if s.is_executable():
            exe_by_lang[s.language] = exe_by_lang.get(s.language, 0) + 1
    print(f"Dataset: {path}")
    print(f"Total records: {len(scenarios)}")
    for lang in sorted(by_lang):
        print(f"  {lang}: {by_lang[lang]} total, {exe_by_lang.get(lang, 0)} executable")
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    sys.exit(validate_cli(argv))


if __name__ == "__main__":
    main()

"""Configuration loading for EthioContextEval pilot experiments."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


SUPPORTED_LANGUAGES = ("en", "am", "om")
SUPPORTED_DOMAINS = (
    "education",
    "public_services",
    "business_finance",
    "ethiopian_contextual_reasoning",
)
SUPPORTED_PROVIDERS = ("mock", "bedrock")

# Domain aliases accepted in datasets
DOMAIN_ALIASES = {
    "education": "education",
    "edu": "education",
    "public_services": "public_services",
    "public-services": "public_services",
    "gov": "public_services",
    "government": "public_services",
    "business_finance": "business_finance",
    "business/finance": "business_finance",
    "business": "business_finance",
    "finance": "business_finance",
    "bus": "business_finance",
    "ethiopian_contextual_reasoning": "ethiopian_contextual_reasoning",
    "ethiopian-contextual-reasoning": "ethiopian_contextual_reasoning",
    "contextual_reasoning": "ethiopian_contextual_reasoning",
    "context": "ethiopian_contextual_reasoning",
    "ctx": "ethiopian_contextual_reasoning",
}

DOMAIN_CODES = {
    "education": "EDU",
    "public_services": "PUB",
    "business_finance": "BIZ",
    "ethiopian_contextual_reasoning": "CTX",
    "edu": "education",
    "pub": "public_services",
    "biz": "business_finance",
    "ctx": "ethiopian_contextual_reasoning",
}


def repo_root() -> Path:
    """Return repository root (parent of src/)."""
    return Path(__file__).resolve().parents[2]


@dataclass
class ModelConfig:
    """One model entry from config/models*.json."""

    name: str
    model_id: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ModelConfig:
        return cls(
            name=str(raw.get("name") or raw.get("model_id") or "unnamed"),
            model_id=str(raw["model_id"]),
            enabled=bool(raw.get("enabled", True)),
        )


@dataclass
class PilotConfig:
    """Runtime configuration for pilot generation and analysis."""

    provider: str = "bedrock"
    aws_region: str = "us-east-1"
    aws_profile: str | None = None
    max_tokens: int = 500
    temperature: float = 0.0
    runs: int = 2
    dataset_path: Path = field(default_factory=lambda: repo_root() / "data" / "scenarios.jsonl")
    models_config_path: Path = field(
        default_factory=lambda: repo_root() / "config" / "models.bedrock.json"
    )
    results_dir: Path = field(default_factory=lambda: repo_root() / "results")
    models: list[ModelConfig] = field(default_factory=list)
    allow_unvalidated: bool = False

    def enabled_models(self) -> list[ModelConfig]:
        return [m for m in self.models if m.enabled]

    @property
    def raw_dir(self) -> Path:
        return self.results_dir / "raw"

    @property
    def blinded_dir(self) -> Path:
        return self.results_dir / "blinded"

    @property
    def ratings_dir(self) -> Path:
        return self.results_dir / "ratings"

    @property
    def analysis_dir(self) -> Path:
        return self.results_dir / "analysis"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def load_models_config(path: Path | str) -> tuple[str | None, list[ModelConfig]]:
    """Load optional provider + model list from JSON."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Model configuration not found: {path}")
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    provider = payload.get("provider") if isinstance(payload, dict) else None
    if provider is not None:
        provider = str(provider).strip().lower()
    models_raw = payload if isinstance(payload, list) else payload.get("models", [])
    models = [ModelConfig.from_dict(m) for m in models_raw]
    return provider, models


def default_models_path() -> Path:
    root = repo_root()
    # Preference: explicit env, models.json, models.bedrock.json, models.example.json
    env_path = os.getenv("ETHIOEVAL_CONFIG")
    if env_path:
        return Path(env_path)
    for candidate in (
        root / "config" / "models.json",
        root / "config" / "models.bedrock.json",
        root / "config" / "models.bedrock.example.json",
    ):
        if candidate.is_file():
            return candidate
    return root / "config" / "models.bedrock.json"


def load_config(
    *,
    dotenv_path: Path | str | None = None,
    models_config_path: Path | str | None = None,
    dataset_path: Path | str | None = None,
    results_dir: Path | str | None = None,
    provider: str | None = None,
) -> PilotConfig:
    """Load PilotConfig from env + optional models JSON."""
    root = repo_root()
    env_file = Path(dotenv_path) if dotenv_path else root / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        load_dotenv()

    models_path = (
        Path(models_config_path)
        if models_config_path
        else (root / "config" / "models.mock.json" if provider == "mock" else default_models_path())
    )
    file_provider, models = load_models_config(models_path)

    # Optional region/profile from models JSON
    json_region: str | None = None
    json_profile: str | None = None
    if models_path.is_file():
        with models_path.open(encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            if payload.get("region"):
                json_region = str(payload["region"]).strip()
            if payload.get("aws_profile"):
                json_profile = str(payload["aws_profile"]).strip()

    resolved_provider = (
        (provider or os.getenv("ETHIOEVAL_PROVIDER") or file_provider or "bedrock").strip().lower()
    )
    if resolved_provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            "Provider 'ollama' has been removed. Use 'bedrock' (or 'mock' for offline tests)."
        )

    cfg = PilotConfig(
        provider=resolved_provider,
        aws_region=(
            os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or json_region or "us-east-1"
        ),
        aws_profile=os.getenv("AWS_PROFILE") or json_profile,
        max_tokens=_env_int("ETHIOEVAL_MAX_TOKENS", 500),
        temperature=_env_float("ETHIOEVAL_TEMPERATURE", 0.0),
        runs=_env_int("ETHIOEVAL_RUNS", 2),
        dataset_path=Path(dataset_path)
        if dataset_path
        else Path(
            os.getenv(
                "ETHIOEVAL_DATASET",
                os.getenv("ETHIOEVAL_DATA", str(root / "data" / "scenarios.jsonl")),
            )
        ),
        models_config_path=models_path,
        results_dir=Path(results_dir)
        if results_dir
        else Path(
            os.getenv(
                "ETHIOEVAL_RESULTS", os.getenv("ETHIOEVAL_RESULTS_DIR", str(root / "results"))
            )
        ),
        models=models,
        allow_unvalidated=os.getenv("ETHIOEVAL_ALLOW_UNVALIDATED", "").lower()
        in {"1", "true", "yes"},
    )
    return cfg

"""Configuration loading for EthioContextEval pilot experiments."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

SUPPORTED_LANGUAGES = ("en", "am", "om")
SUPPORTED_DOMAINS = (
    "education",
    "public_services",
    "business_finance",
    "ethiopian_contextual_reasoning",
)

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

DEFAULT_MODEL_IDS = {
    "nova-lite": "amazon.nova-lite-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
}


def repo_root() -> Path:
    """Return repository root (parent of src/)."""
    return Path(__file__).resolve().parents[2]


@dataclass
class ModelConfig:
    """Single model entry from config/models.json."""

    name: str
    model_id: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        return cls(
            name=str(data["name"]),
            model_id=str(data["model_id"]),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class PilotConfig:
    """Runtime configuration for pilot generation and analysis."""

    aws_region: str = "us-east-1"
    max_tokens: int = 500
    temperature: float = 0.0
    runs: int = 2
    dataset_path: Path = field(default_factory=lambda: repo_root() / "data" / "scenarios.jsonl")
    models_config_path: Path = field(
        default_factory=lambda: repo_root() / "config" / "models.example.json"
    )
    results_dir: Path = field(default_factory=lambda: repo_root() / "results")
    models: list[ModelConfig] = field(default_factory=list)

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


def load_models_config(path: Path | str) -> list[ModelConfig]:
    """Load model list from JSON. Falls back to example defaults if missing."""
    path = Path(path)
    if not path.is_file():
        example = repo_root() / "config" / "models.example.json"
        if example.is_file():
            path = example
        else:
            return [
                ModelConfig(name=n, model_id=mid, enabled=True)
                for n, mid in DEFAULT_MODEL_IDS.items()
            ]
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    models_raw = payload.get("models", payload if isinstance(payload, list) else [])
    return [ModelConfig.from_dict(item) for item in models_raw]


def load_config(
    *,
    dotenv_path: Path | str | None = None,
    models_config_path: Path | str | None = None,
    dataset_path: Path | str | None = None,
    results_dir: Path | str | None = None,
) -> PilotConfig:
    """
    Load pilot configuration from environment and optional JSON.

    AWS credentials are never read from project source files. boto3 uses the
    standard credential chain (env, shared config, IAM role, etc.).
    """
    root = repo_root()
    env_file = Path(dotenv_path) if dotenv_path else root / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        load_dotenv()

    models_path = Path(models_config_path) if models_config_path else None
    if models_path is None:
        local_models = root / "config" / "models.json"
        models_path = local_models if local_models.is_file() else root / "config" / "models.example.json"

    cfg = PilotConfig(
        aws_region=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-1",
        max_tokens=_env_int("ETHIOEVAL_MAX_TOKENS", 500),
        temperature=_env_float("ETHIOEVAL_TEMPERATURE", 0.0),
        runs=_env_int("ETHIOEVAL_RUNS", 2),
        dataset_path=Path(dataset_path)
        if dataset_path
        else Path(os.getenv("ETHIOEVAL_DATA", str(root / "data" / "scenarios.jsonl"))),
        models_config_path=models_path,
        results_dir=Path(results_dir)
        if results_dir
        else Path(os.getenv("ETHIOEVAL_RESULTS_DIR", str(root / "results"))),
        models=load_models_config(models_path),
    )
    return cfg

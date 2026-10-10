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
SUPPORTED_PROVIDERS = ("mock", "ollama", "bedrock")

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

DEFAULT_LOCAL_MODELS = {
    "qwen-local": "qwen2.5:7b",
    "gemma-local": "gemma3:4b",
}


def repo_root() -> Path:
    """Return repository root (parent of src/)."""
    return Path(__file__).resolve().parents[2]


@dataclass
class ModelConfig:
    """Single model entry from config JSON."""

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

    provider: str = "ollama"
    aws_region: str = "us-east-1"
    ollama_base_url: str = "http://localhost:11434"
    max_tokens: int = 500
    temperature: float = 0.0
    runs: int = 2
    dataset_path: Path = field(default_factory=lambda: repo_root() / "data" / "scenarios.jsonl")
    models_config_path: Path = field(
        default_factory=lambda: repo_root() / "config" / "models.local.json"
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


def load_models_config(path: Path | str) -> tuple[str | None, list[ModelConfig]]:
    """Load optional provider + model list from JSON."""
    path = Path(path)
    if not path.is_file():
        local = repo_root() / "config" / "models.local.json"
        example_local = local
        bedrock_example = repo_root() / "config" / "models.example.json"
        if example_local.is_file():
            path = example_local
        elif bedrock_example.is_file():
            path = bedrock_example
        else:
            return "ollama", [
                ModelConfig(name=n, model_id=mid, enabled=True)
                for n, mid in DEFAULT_LOCAL_MODELS.items()
            ]
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    provider = payload.get("provider")
    if provider is not None:
        provider = str(provider).strip().lower()
    models_raw = payload.get("models", payload if isinstance(payload, list) else [])
    models = [ModelConfig.from_dict(item) for item in models_raw]
    return provider, models


def _default_models_path() -> Path:
    root = repo_root()
    # Preference: explicit env, local models.json, models.local.json, bedrock example
    env_path = os.getenv("ETHIOEVAL_CONFIG")
    if env_path:
        return Path(env_path)
    for candidate in (
        root / "config" / "models.json",
        root / "config" / "models.local.json",
        root / "config" / "models.example.json",
    ):
        if candidate.is_file():
            return candidate
    return root / "config" / "models.local.json"


def load_config(
    *,
    dotenv_path: Path | str | None = None,
    models_config_path: Path | str | None = None,
    dataset_path: Path | str | None = None,
    results_dir: Path | str | None = None,
    provider: str | None = None,
) -> PilotConfig:
    """
    Load pilot configuration from environment and optional JSON.

    AWS credentials are never read from project source files. boto3 (when used)
    uses the standard credential chain. Local Ollama needs no cloud account.
    """
    root = repo_root()
    env_file = Path(dotenv_path) if dotenv_path else root / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        load_dotenv()

    models_path = Path(models_config_path) if models_config_path else _default_models_path()
    file_provider, models = load_models_config(models_path)

    resolved_provider = (
        (provider or os.getenv("ETHIOEVAL_PROVIDER") or file_provider or "ollama")
        .strip()
        .lower()
    )

    cfg = PilotConfig(
        provider=resolved_provider,
        aws_region=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-1",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
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
        models=models,
    )
    return cfg

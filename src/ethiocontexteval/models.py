"""Model discovery helpers (CLI: python -m ethiocontexteval.models)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from ethiocontexteval.config import load_config
from ethiocontexteval.providers import ProviderError, get_provider


def list_models_cli(
    provider_name: str,
    *,
    region: str | None = None,
    base_url: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            base_url=base_url or cfg.ollama_base_url,
        )
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 1

    health = provider.health_check()
    print(f"Provider: {provider.provider_name()}")
    print(f"Health: ok={health.get('ok')} — {health.get('message')}")
    if not health.get("ok") and provider.provider_name() != "mock":
        return 1

    try:
        models = provider.list_models()
    except ProviderError as exc:
        print(f"ERROR listing models: {exc}")
        return 1

    print(f"Models visible: {len(models)}")
    print("-" * 80)
    for m in models:
        print(f"  - {m.model_id}" + (f" ({m.name})" if m.name and m.name != m.model_id else ""))
        if m.metadata:
            # keep listing compact
            keys = list(m.metadata.keys())[:5]
            if keys:
                print(f"      meta keys: {', '.join(keys)}")

    print()
    print("Configured pilot models:")
    for mc in cfg.models:
        flag = "enabled" if mc.enabled else "disabled"
        available = "unknown"
        try:
            provider.ensure_model_available(mc.model_id)
            available = "available"
        except ProviderError:
            available = "NOT FOUND / not installed"
        except Exception as exc:  # noqa: BLE001
            available = f"check_failed ({exc})"
        print(f"  - {mc.name}: {mc.model_id} [{flag}] -> {available}")
    return 0


def health_cli(
    provider_name: str,
    *,
    region: str | None = None,
    base_url: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            base_url=base_url or cfg.ollama_base_url,
        )
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 1
    health = provider.health_check()
    print(json.dumps(health, indent=2, default=str))
    return 0 if health.get("ok") else 1


def check_configured(
    provider_name: str,
    *,
    region: str | None = None,
    base_url: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            base_url=base_url or cfg.ollama_base_url,
        )
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 1
    ok = True
    health = provider.health_check()
    if not health.get("ok"):
        print(f"Health failed: {health.get('message')}")
        return 2
    for mc in cfg.enabled_models():
        try:
            provider.ensure_model_available(mc.model_id)
            print(f"OK: {mc.name} ({mc.model_id})")
        except ProviderError as exc:
            ok = False
            print(f"MISSING: {mc.name} ({mc.model_id})")
            print(f"  {exc}")
    return 0 if ok else 2


def dump_json(
    provider_name: str,
    *,
    region: str | None = None,
    base_url: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    provider = get_provider(
        provider_name,
        region=region or cfg.aws_region,
        base_url=base_url or cfg.ollama_base_url,
    )
    models = provider.list_models()
    print(json.dumps([m.to_dict() for m in models], indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.models",
        description="Discover and verify models for a chosen provider.",
    )
    parser.add_argument(
        "command",
        choices=["list", "check", "health", "json"],
        help="list | check configured | health | json dump",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="mock | ollama | bedrock (default from config / ollama)",
    )
    parser.add_argument("--region", default=None, help="AWS region override (bedrock)")
    parser.add_argument("--ollama-url", default=None, help="Ollama base URL")
    parser.add_argument(
        "--config",
        default=None,
        help="Models config JSON path",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = load_config(models_config_path=args.config, provider=args.provider)
    provider_name = (args.provider or cfg.provider or "ollama").strip().lower()

    if args.command == "list":
        code = list_models_cli(
            provider_name, region=args.region, base_url=args.ollama_url
        )
    elif args.command == "check":
        code = check_configured(
            provider_name, region=args.region, base_url=args.ollama_url
        )
    elif args.command == "health":
        code = health_cli(
            provider_name, region=args.region, base_url=args.ollama_url
        )
    else:
        code = dump_json(
            provider_name, region=args.region, base_url=args.ollama_url
        )
    sys.exit(code)


if __name__ == "__main__":
    main()

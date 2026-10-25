"""Model discovery helpers (CLI: python -m madaala.models)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from madaala.config import load_config
from madaala.providers import ProviderError, get_provider


def _print_health(provider_name: str, health: dict) -> None:
    print(json.dumps(health, indent=2, default=str))
    if not health.get("ok"):
        print(f"Health check failed for provider '{provider_name}'", file=sys.stderr)


def health_cli(
    provider_name: str,
    *,
    region: str | None = None,
    profile: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            profile=profile or cfg.aws_profile,
        )
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 2
    health = provider.health_check()
    _print_health(provider_name, health)
    return 0 if health.get("ok") else 1


def list_cli(
    provider_name: str,
    *,
    region: str | None = None,
    profile: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            profile=profile or cfg.aws_profile,
        )
        models = provider.list_models()
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps([m.to_dict() for m in models], indent=2, default=str))
    print(f"\n{len(models)} model(s) listed for provider '{provider_name}'.")
    return 0


def check_cli(
    provider_name: str,
    *,
    region: str | None = None,
    profile: str | None = None,
    config_path: str | None = None,
) -> int:
    cfg = load_config(provider=provider_name, models_config_path=config_path)
    try:
        provider = get_provider(
            provider_name,
            region=region or cfg.aws_region,
            profile=profile or cfg.aws_profile,
        )
    except ProviderError as exc:
        print(f"ERROR: {exc}")
        return 2
    if not cfg.enabled_models():
        print("No enabled models in config.")
        return 1
    failures = 0
    for mc in cfg.enabled_models():
        try:
            provider.ensure_model_available(mc.model_id)
            print(f"OK: {mc.name} ({mc.model_id})")
        except ProviderError as exc:
            failures += 1
            print(f"FAIL: {mc.name} ({mc.model_id})")
            print(f"  {exc}")
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m madaala.models",
        description="Discover and verify models for Bedrock (or mock).",
    )
    parser.add_argument(
        "command",
        choices=["health", "list", "check"],
        help="health | list | check",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=["mock", "bedrock"],
        help="Provider (default: config / MADAALA_PROVIDER / bedrock)",
    )
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--profile", default=None, help="AWS profile override")
    parser.add_argument(
        "--config",
        default=None,
        help="Models JSON path (for check)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    cfg = load_config(provider=args.provider, models_config_path=args.config)
    provider_name = args.provider or cfg.provider

    if args.command == "health":
        code = health_cli(provider_name, region=args.region, profile=args.profile)
    elif args.command == "list":
        code = list_cli(provider_name, region=args.region, profile=args.profile)
    else:
        code = check_cli(
            provider_name,
            region=args.region,
            profile=args.profile,
            config_path=args.config,
        )
    raise SystemExit(code)


if __name__ == "__main__":
    main()

"""Model discovery and configuration helpers (CLI: python -m ethiocontexteval.models)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from ethiocontexteval.bedrock_client import BedrockClient
from ethiocontexteval.config import load_config


def list_models_cli(region: str | None = None, provider: str | None = None) -> int:
    cfg = load_config()
    region_name = region or cfg.aws_region
    client = BedrockClient(region_name=region_name)
    try:
        models = client.list_foundation_models(by_provider=provider)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to list foundation models in region '{region_name}': {exc}")
        print(
            "Check AWS credentials (aws sts get-caller-identity), region, "
            "and Bedrock permissions (bedrock:ListFoundationModels)."
        )
        return 1

    if not models:
        print(f"No foundation models returned for region '{region_name}'.")
        return 0

    # Stable sort
    models = sorted(
        models,
        key=lambda m: (
            str(m.get("provider") or ""),
            str(m.get("model_name") or ""),
            str(m.get("model_id") or ""),
        ),
    )

    print(f"Region: {region_name}")
    print(f"Foundation models: {len(models)}")
    print("-" * 100)
    header = (
        f"{'PROVIDER':<16} {'MODEL NAME':<28} {'MODEL ID':<42} "
        f"{'IN':<12} {'OUT':<12} {'INFER':<16}"
    )
    print(header)
    print("-" * 100)
    for m in models:
        provider_s = str(m.get("provider") or "")[:16]
        name = str(m.get("model_name") or "")[:28]
        mid = str(m.get("model_id") or "")[:42]
        inn = ",".join(m.get("input_modalities") or [])[:12]
        out = ",".join(m.get("output_modalities") or [])[:12]
        infer = ",".join(m.get("inference_types") or [])[:16]
        print(f"{provider_s:<16} {name:<28} {mid:<42} {inn:<12} {out:<12} {infer:<16}")

    # Compare configured pilot models
    print()
    print("Configured pilot models:")
    for mc in cfg.models:
        flag = "enabled" if mc.enabled else "disabled"
        available = "unknown"
        try:
            available = "available" if client.is_model_available(mc.model_id) else "NOT FOUND"
        except Exception:  # noqa: BLE001
            available = "check_failed"
        print(f"  - {mc.name}: {mc.model_id} [{flag}] -> {available}")
    return 0


def check_configured(region: str | None = None) -> int:
    cfg = load_config()
    region_name = region or cfg.aws_region
    client = BedrockClient(region_name=region_name)
    ok = True
    for mc in cfg.enabled_models():
        try:
            client.ensure_model_available(mc.model_id)
            print(f"OK: {mc.name} ({mc.model_id})")
        except RuntimeError as exc:
            ok = False
            print(f"MISSING: {mc.name} ({mc.model_id})")
            print(f"  {exc}")
    return 0 if ok else 2


def dump_json(region: str | None = None) -> int:
    cfg = load_config()
    region_name = region or cfg.aws_region
    client = BedrockClient(region_name=region_name)
    models = client.list_foundation_models()
    print(json.dumps(models, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ethiocontexteval.models",
        description="Discover and verify Amazon Bedrock foundation models.",
    )
    parser.add_argument(
        "command",
        choices=["list", "check", "json"],
        help="list: human table; check: verify configured models; json: raw dump",
    )
    parser.add_argument("--region", default=None, help="AWS region override")
    parser.add_argument("--provider", default=None, help="Filter list by provider name")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "list":
        code = list_models_cli(region=args.region, provider=args.provider)
    elif args.command == "check":
        code = check_configured(region=args.region)
    else:
        code = dump_json(region=args.region)
    sys.exit(code)


if __name__ == "__main__":
    main()

"""Read-only Bedrock Service Quotas diagnostics; never invokes a model."""

from __future__ import annotations

import argparse
import json


def inspect_quotas(client, search: str = "") -> dict:
    """Return matching applied quotas. Name matches are advisory, never model guarantees."""
    rows = []
    for page in client.get_paginator("list_service_quotas").paginate(ServiceCode="bedrock"):
        for quota in page.get("Quotas", []):
            name = quota.get("QuotaName", "")
            if search.casefold() in name.casefold():
                rows.append(
                    {
                        "name": name,
                        "value": quota.get("Value"),
                        "code": quota.get("QuotaCode"),
                        "adjustable": quota.get("Adjustable"),
                    }
                )
    return {
        "quotas": rows,
        "zero_quota_warning": any(q["value"] == 0 for q in rows),
        "note": "Name matching is advisory. Verify the exact model, inference mode, account and region in Service Quotas. Discovery does not establish runtime capacity.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Optional AWS named profile")
    parser.add_argument("--region", default="eu-north-1", help="AWS region")
    parser.add_argument(
        "--search", default="", help="Case-insensitive quota-name substring, e.g. Qwen"
    )
    args = parser.parse_args()
    try:
        import boto3

        from madaala.bedrock_client import format_aws_error

        session = boto3.Session(profile_name=args.profile, region_name=args.region)
        report = inspect_quotas(session.client("service-quotas"), args.search)
        print(json.dumps(report, indent=2))
        if report["zero_quota_warning"]:
            print(
                "WARNING: The model may be visible in Amazon Bedrock, but the AWS account may have zero runtime RPM/TPM quota. Check the exact model and region manually."
            )
    except Exception as exc:
        print(format_aws_error(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail
profile="${1:-}"
region="${2:-eu-north-1}"
aws_options=(--region "$region" --no-cli-pager)
if [[ -n "$profile" ]]; then aws_options+=(--profile "$profile"); fi
aws --version
aws sts get-caller-identity "${aws_options[@]}"
aws bedrock list-foundation-models "${aws_options[@]}" --query 'modelSummaries[:10].[modelId,modelName]' --output table
printf '%s\n' 'Discovery only. Runtime access and quota remain unverified. No inference was sent.'

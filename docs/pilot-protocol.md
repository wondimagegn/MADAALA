# MADAALA pilot protocol

This protocol exercises the current 12-scenario MADAALA dataset. The expanded research design is described in the [methodology](methodology.md) and [roadmap](madaala-roadmap.md).

## Prerequisites

Run from the repository root in an activated Python environment after `python -m pip install -e ".[dev]"`. Offline mock runs need no AWS account. Bedrock runs require authenticated AWS access, a configured model and usable runtime quotas. See the [README](../README.md) for platform-specific setup.

## Validate and plan offline

```text
python -m madaala.dataset validate data/scenarios.jsonl
python -m madaala.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --dry-run
```

Expect 36 valid records, 12 executable by default and 24 draft records skipped. The filtered plan contains one generation.

## Execute a synthetic smoke test

Choose an unused output path for a new experiment:

```text
python -m madaala.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --execute --output results/raw/madaala_mock_smoke.jsonl
```

Mock responses verify the pipeline and are not experimental findings.

## Prepare a Bedrock run

Copy `config/models.bedrock.example.json` to the local, ignored `config/models.bedrock.json` if it does not already exist. Select an exact model ID and region supported by your account. Replace `madaala` below with your configured AWS profile name.

```text
python -m madaala.models check --provider bedrock --profile madaala --region eu-north-1 --config config/models.bedrock.json
python -m madaala.quotas --profile madaala --region eu-north-1 --search Qwen
python -m madaala.runner --provider bedrock --profile madaala --region eu-north-1 --config config/models.bedrock.json --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 --runs 1 --temperature 0 --max-tokens 1000 --dry-run
```

Discovery does not establish inference permission or capacity; dry-run is an offline plan. Confirm one selected record, one model and one expected generation. When ready to incur inference charges, replace `--dry-run` with `--execute --output results/raw/madaala_bedrock_smoke.jsonl` using a fresh path. Transient failures can trigger bounded retries.

For technical tests in Amharic or Afaan Oromo, select `--language am` or `--language om` and add `--allow-unvalidated`. All current records remain technical-only, including English. Expert review must precede research comparisons.

## Review and collect human ratings

Inspect status, errors, response text, finish reason and validation metadata. API success does not establish accuracy; `finish_reason=max_tokens` may indicate incomplete output. Calibrate budgets before expanding runs.

For a completed experiment, substitute its actual response path:

```text
python -m madaala.anonymize results/raw/madaala_bedrock_smoke.jsonl --blinded-out results/blinded/madaala_pilot.csv --mapping-out results/raw/blind_mapping_madaala_pilot.csv
python -m madaala.human_evaluation template results/blinded/madaala_pilot.csv --out results/ratings/madaala_reviewer1.csv
```

Provide reviewers with the matching prompts and [annotation guidelines](annotation-guidelines.md). Use separate files and evaluator IDs for independent reviewers. Keep the mapping private. Analyze only genuine completed ratings under documented inclusion rules; see the [output guide](proposal-outputs.md).

## Run controls

- Resolve invalid data, unknown models and access failures before execution.
- Use separate output paths for changed prompts or generation settings.
- Record dataset version/hash, code commit, model, region, settings and validation status.
- Keep raw responses and private mappings out of Git.
- Report truncation, failures and exclusions explicitly.
- Base quality conclusions on validated prompts and qualified human evaluation.

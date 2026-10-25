# MADAALA developer guide

## Start here

Read [README.md](../README.md) for Windows/Linux installation and the beginner model-running walkthrough. Use Python 3.11+ and install the editable package with development tools:

```text
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check src tests
```

Run from the repository root with the virtual environment active. No AWS account is required for offline development. Use a feature branch and a PR for changes; do not commit local credentials, raw generations or blind mappings.

## Architecture and data flow

```text
models JSON + optional environment + CLI overrides
    -> config.PilotConfig
scenarios JSONL -> dataset.load_scenarios
    -> runner filtering and plan_requests
    -> providers.get_provider -> ModelProvider.generate
    -> normalized GenerationResult -> incremental generation JSONL
    -> anonymize -> blinded CSV + private mapping
    -> human_evaluation -> blank templates -> independent human ratings
    -> metrics + analysis -> tables, figures and report
```

| Module under src/madaala/ | Responsibility |
|---|---|
| config.py | ModelConfig/PilotConfig, model JSON, environment defaults and paths |
| dataset.py | Scenario schema, structural validation, execution and research-grade decisions |
| runner.py | CLI, exact filtering, planning, execution, JSONL logging and resume |
| providers/base.py | ModelProvider interface, normalized result/catalog types, provider factory |
| providers/mock_provider.py | Synthetic offline responses for development and CI |
| providers/bedrock_provider.py | Bedrock adapter implementing the shared interface |
| bedrock_client.py | boto3 control/runtime clients, Converse requests and retries |
| models.py / quotas.py | Read-only discovery and advisory quota diagnostics |
| anonymize.py | Blinded packets and private identity mapping |
| human_evaluation.py | Rating rubric fields, templates and CSV loading |
| metrics.py | Score aggregation and language/context/safety gap calculations |
| analysis.py | Statistical helpers, tables, figures and Markdown report |

Tests in tests/ cover datasets, provider normalization, filtering, dry-run safety, technical-pilot metadata, resume, anonymization and metrics. AWS tests inject fake clients; they do not contact AWS. GitHub Actions checks Windows/Linux on Python 3.11/3.12.

## Add a model already supported by Bedrock

1. Copy config/models.bedrock.example.json to the ignored local config/models.bedrock.json.
2. Add an exact model ID, readable name and enabled flag. Check the region and model's Converse support.
3. Use models list/check and quota diagnostics from the README. Discovery is not proof of inference capacity.
4. Dry-run one scenario, one language, one model and one run. Review the count.
5. Run paid inference only when its cost/scope is authorized, using a new output path.

This normally requires configuration changes only. Do not add model-specific branches to the runner when the shared Converse adapter already supports the model.

## Add a new provider

1. Create a module in providers/ and subclass ModelProvider from providers/base.py.
2. Implement provider_name(), health_check(), list_models() and generate(). Return ModelInfo catalog entries and GenerationResult responses.
3. Keep health/discovery read-only. Use exact discovery IDs; document separately how provider-specific inference profiles are verified.
4. Return useful status=error results for generation failures. Leave unknown usage fields null rather than estimating tokens. Never return credentials in metadata.
5. Register it in get_provider(), add it to SUPPORTED_PROVIDERS in config.py and update provider choices in runner.py/models.py.
6. Add an example config, fake-client tests and documentation. SDK dependencies belong in pyproject.toml, the runtime dependency source; requirements files delegate to it.

Use MockProvider and the injected-client Bedrock tests as examples. Preserve normalized JSONL compatibility for downstream blinding/rating tools. If a new provider needs extra configuration, extend PilotConfig and the factory deliberately rather than bypassing the interface.

## Extend scenarios, translations or languages

For new scenarios, add unique (scenario_id, language, variant) records with the fields documented in docs/data-schema.md. Keep the user intent, expected behavior, numeric constraints and safety requirements matched across languages. Do not silently alter existing research prompts or validation provenance.

For the proposed benchmark, author each language realization from a shared intent specification and validate equivalence. For the current draft translations, follow [prompt review guidance](translation-review.md). Store actual reviewer identities/decisions and preserve pending labels until review is complete. Structural validation cannot establish translation quality.

A new language requires more than a dataset row: update SUPPORTED_LANGUAGES in config.py, runner CLI language choices, display labels, relevant metric/analysis assumptions, reviewer instructions and regression tests. Check for hardcoded en/am/om references before extending. Do not assume the analysis already generalizes to every language.

```text
python -m madaala.dataset validate data/scenarios.jsonl
python -m pytest tests/test_dataset.py tests/test_runner_safety.py
```

## Extend human ratings and metrics

For a new rating dimension, update RATING_DIMENSIONS and TEMPLATE_FIELDS in human_evaluation.py, the annotation guidelines, input validation and analysis/report code. Decide explicitly whether the dimension belongs in DEFAULT_SCORE_DIMENSIONS in metrics.py; safety is excluded from the default composite. Define missing/not-applicable behavior and test it with small known-value fixtures.

For a new metric, implement a pure calculation in metrics.py where practical, integrate it into analysis.py and document its units, pairing, interpretation and limitations. Verify missing ratings, duplicates and multiple evaluators. A blank template is not a dataset of scores. Never fill absent ratings with invented values.

## Experiment and analysis safeguards

- The CLI must require --execute for inference; dry-run must not initialize AWS or send inference requests.
- Keep unknown/disabled model and unknown scenario filters explicit errors; never broaden a requested experiment silently.
- Record validation snapshots, research_grade and technical_pilot. Research-grade metadata is a guard, not a substitute for scientific review.
- Use boto3's credential chain. Profiles/regions are configuration; keys/tokens must never enter code or logs.
- A successful API response can still be wrong or truncated. Inspect finish_reason=max_tokens separately from status=ok.
- Resume identifies provider/scenario/language/variant/model/run, not prompt hashes or generation settings. Use a new output file when those change; successful truncated rows are also skipped on resume.
- Blank ratings and synthetic outputs cannot support research findings. Keep technical-pilot and validated datasets/results distinguishable.

## Known limitations to address when expanding

The runner is sequential and builds an in-memory job list. It provides incremental writes and basic resume, not a distributed batch scheduler. Calibrate output budgets across languages before larger paid runs. Add concurrency only with explicit quota/rate control and reliable logging.

The analysis CLI writes to results/analysis/ and reports/pilot_report.md by default, potentially replacing earlier outputs. The Python run_analysis_pipeline API accepts separate analysis_dir and report_path values. Use unique output locations for each experiment.

The generated report contains template narrative and should be reviewed against the actual dataset, providers, settings and ratings before proposal/publication use. Do not assume it automatically filters all technical-only or truncated records. Apply and document inclusion rules before analysis. Current proposal evidence is indexed in docs/proposal-outputs.md.

SageMaker providers, S3 orchestration, distributed execution and expanded robustness conditions are future extensions, not established capabilities of the current prototype.

## Verify a change before a PR

```text
python -m pytest
python -m ruff check .
python -m ruff format --check src tests
python -m madaala.dataset validate data/scenarios.jsonl
python -m madaala.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --dry-run
git diff --check
```

For changes to execution, also run a mock execution with a fresh output file. Add tests for meaningful new behavior or failures; documentation-only changes need command/path verification. Describe what changed, validation performed, schema compatibility and remaining limitations in the PR. Never run paid inference merely as a test dependency.

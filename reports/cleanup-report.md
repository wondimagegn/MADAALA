# Cleanup and verification report

No commits or paid Bedrock inference were performed. Existing user edits were retained, including the dataset; its SHA-256 remains 778f83c9da9d2508238ad50e89e3d99cec687f8db1256e0005ed21e85f97a93e.

## Before cleanup

Top-level: .github, config, data, docs, reports, results, scripts, src, tests, tools, .audit_tmp, _audit_dump, _audit_full, _full_dump, many _tmp/_dump/_full/_sec files, packaging files, local virtual environment and caches.

Full pre-cleanup inventory is retained locally in reports/cleanup-before.txt (ignored by Git).

## After cleanup

```text
.env.example
.github/workflows/python-tests.yml
.gitignore
LICENSE
README.md
config/models.bedrock.example.json
config/models.mock.json
data/README.md
data/pilot_scenarios_en.jsonl
data/scenarios.jsonl
data/scenarios_before_translation.jsonl
data/smoke_EDU001_en.jsonl
docs/annotation-guidelines.md
docs/data-schema.md
docs/ethics-and-data-governance.md
docs/methodology.md
docs/pilot-protocol.md
pyproject.toml
reports/README.md
reports/dataset.sha256
reports/pilot_report.md
requirements-dev.txt
requirements.txt
results/README.md
results/analysis/.gitkeep
results/analysis/figures/.gitkeep
results/blinded/.gitkeep
results/ratings/.gitkeep
results/raw/.gitkeep
scripts/_build_pilot_dataset.py
scripts/check_aws_environment.ps1
scripts/check_aws_environment.sh
src/ethiocontexteval/__init__.py
src/ethiocontexteval/analysis.py
src/ethiocontexteval/anonymize.py
src/ethiocontexteval/bedrock_client.py
src/ethiocontexteval/config.py
src/ethiocontexteval/dataset.py
src/ethiocontexteval/human_evaluation.py
src/ethiocontexteval/metrics.py
src/ethiocontexteval/models.py
src/ethiocontexteval/providers/__init__.py
src/ethiocontexteval/providers/base.py
src/ethiocontexteval/providers/bedrock_provider.py
src/ethiocontexteval/providers/mock_provider.py
src/ethiocontexteval/quotas.py
src/ethiocontexteval/runner.py
tests/test_anonymize.py
tests/test_bedrock.py
tests/test_dataset.py
tests/test_metrics.py
tests/test_providers.py
tests/test_runner_dry.py
tests/test_runner_safety.py
```

## Removed from repository workspace

These obsolete files were moved recoverably to D:/Project/ethiocontexteval-cleanup-archive after automatic review rejected recursive deletion. They are not research data.

```text
_bedrock_client_numbered.txt
_bedrock_provider_numbered.txt
_dataset_numbered.txt
_dump_base.py
_dump_bedrock_client.py
_dump_bedrock_provider.py
_dump_dataset.py
_dump_runner.py
_dump_test_runner_dry.py
_full_base.py
_full_bedrock_client.py
_full_bedrock_provider.py
_full_dataset_is_exec_area.py
_full_runner.py
_full_test_runner.py
_runner_numbered.txt
_sec_create_run.py
_sec_main.py
_sec_plan.py
_sec_top.py
_tmp_analysis.txt
_tmp_analysis_lines.txt
_tmp_analysis_utf8.py
_tmp_bedrock_client.py
_tmp_bedrock_provider.py
_tmp_config.py
_tmp_dataset.txt
_tmp_dataset_lines.txt
_tmp_dataset_utf8.py
_tmp_method.txt
_tmp_method_utf8.md
_tmp_providers_init.py
_tmp_readme.txt
_tmp_readme_utf8.md
_tmp_runner.txt
_tmp_runner_full.py
_tmp_runner_lines.txt
_tmp_runner_mid.py
_tmp_runner_utf8.py
_tmp_runner_view.txt
_tmp_test_ds.py
_tmp_test_runner.py
.audit_tmp
_audit_dump
_audit_full
_full_dump
tools
config\models.local.json
config\models.smoke.json
config\models.example.json
config\models.bedrock.haiku.json
config\models.bedrock.smoke.json
config\models.bedrock.smoke.active.json
scripts\run_local_pilot.ps1
scripts\run_pilot.ps1
scripts\check_environment.ps1
scripts\wait_and_smoke_bedrock.py
src\ethiocontexteval\providers\ollama_provider.py

```

Research data, historical output, documentation, original translation backup, English subset, evaluation rubric and analysis tools were preserved. Generated diagnostics remain local/ignored.

## Added and modified files

This status includes modifications already present when work began. The dataset's pre-existing modification was not changed by cleanup.

```text
 M .env.example
 M .github/workflows/python-tests.yml
 M .gitignore
 M README.md
 D config/models.example.json
 D config/models.local.json
 D config/models.smoke.json
 M data/README.md
 M data/scenarios.jsonl
 M docs/data-schema.md
 M docs/methodology.md
 M docs/pilot-protocol.md
 M pyproject.toml
 M requirements-dev.txt
 M requirements.txt
 D scripts/check_environment.ps1
 D scripts/run_local_pilot.ps1
 D scripts/run_pilot.ps1
 M src/ethiocontexteval/analysis.py
 M src/ethiocontexteval/bedrock_client.py
 M src/ethiocontexteval/config.py
 M src/ethiocontexteval/dataset.py
 M src/ethiocontexteval/human_evaluation.py
 M src/ethiocontexteval/models.py
 M src/ethiocontexteval/providers/base.py
 M src/ethiocontexteval/providers/bedrock_provider.py
 D src/ethiocontexteval/providers/ollama_provider.py
 M src/ethiocontexteval/runner.py
 M tests/test_dataset.py
 M tests/test_metrics.py
 M tests/test_providers.py
 M tests/test_runner_dry.py
?? config/models.bedrock.example.json
?? data/scenarios_before_translation.jsonl
?? data/smoke_EDU001_en.jsonl
?? reports/dataset.sha256
?? scripts/check_aws_environment.ps1
?? scripts/check_aws_environment.sh
?? src/ethiocontexteval/quotas.py
?? tests/test_bedrock.py
?? tests/test_runner_safety.py

```

## Major decisions

- Finished the partially applied Bedrock/mock transition; removed stale Ollama provider/configs/installers and replaced obsolete provider tests.
- Fixed missing dataset constants, runner CLI crash, config lookup, exact model discovery, nested output paths, missing resume paths and per-generation exception recording.
- Kept dry runs entirely offline; paid inference requires --execute. Added positive run/token and temperature checks.
- Preserved translation/validation snapshots. English feasibility execution remains allowed, but pending expert validation means technical-only outputs, including English.
- Added paginated advisory Service Quotas diagnostics without fixed quota IDs or inference.
- Included recent boto3/CRT dependencies, consolidated requirements via pyproject and added Windows/Linux CI.
- Replaced setup documentation with cross-platform commands and AWS access/quota guidance.

## Verification

- Editable installation: python -m pip install --no-deps -e . successfully built and installed the package using isolated build dependencies. An initial no-build-isolation attempt failed because the existing virtual environment lacks wheel; normal installation succeeds. Runtime dependencies were already present and were not reinstalled.
- pytest: 31 passed.
- ruff check .: all checks passed.
- ruff format --check src tests: 22 files already formatted.
- Dataset validation: VALID, 36 records, 12 executable, 24 non-executable by default.
- Dataset bytes: unchanged from start of this task (hash above).
- Mock dry run: exactly 1 generation planned; no inference requests.
- Mock execution: exactly 1 successful synthetic JSONL row in results/raw/refactor_mock_smoke.jsonl, with validation snapshots and technical-pilot flags.
- Security scan: no likely access keys or populated AWS secret/token assignments in tracked and shareable untracked files. Credential-name references occur in CI as empty environment values only. Git history and ignored local secret files were not audited.
- Native tests ran on Windows. Linux execution requires CI/manual confirmation; Windows/Linux CI matrix was added. No live AWS checks were made.

## Complete runner --help

```text
usage: python -m ethiocontexteval.runner [-h] [--provider {mock,bedrock}]
                                         [--config CONFIG] [--dataset DATASET]
                                         [--profile PROFILE]
                                         [--scenario SCENARIO]
                                         [--language {en,am,om}]
                                         [--model MODEL] [--allow-unvalidated]
                                         [--dry-run] [--execute]
                                         [--output OUTPUT]
                                         [--resume-from RESUME_FROM]
                                         [--skip-model-check]
                                         [--region REGION] [--runs RUNS]
                                         [--max-tokens MAX_TOKENS]
                                         [--temperature TEMPERATURE]

Run EthioContextEval pilot generations (provider-independent).

options:
  -h, --help            show this help message and exit
  --provider {mock,bedrock}
                        Inference provider (default from config /
                        ETHIOEVAL_PROVIDER / bedrock)
  --config CONFIG       Path to models JSON (e.g. config/models.bedrock.json)
  --dataset DATASET     Path to scenarios JSONL (default from config)
  --profile PROFILE     AWS profile name for Bedrock authentication
  --scenario SCENARIO   Run only the specified scenario_id
  --language {en,am,om}
                        Run only the specified language
  --model MODEL         Run only the specified configured model_id
  --allow-unvalidated   Allow pending/unvalidated language records for
                        technical-pilot execution
  --dry-run             Validate and plan only; do not call any model
  --execute             Execute model inference (requires explicit flag)
  --output OUTPUT       Output JSONL path for generations
  --resume-from RESUME_FROM
                        Prior generations JSONL to skip completed ok rows
  --skip-model-check    Do not pre-check model availability
  --region REGION       AWS region (bedrock only)
  --runs RUNS           Override repeated runs
  --max-tokens MAX_TOKENS
                        Maximum output tokens per generation
  --temperature TEMPERATURE
                        Sampling temperature (0 to 1)

```

## Exact setup commands and manual AWS steps

README.md contains separate complete Windows PowerShell and Linux/bash clone/install/validation/dry-run commands, plus one paid generation command usable in both shells, mock checks and technical multilingual pilot instructions.

Manual AWS work remains: install CLI v2, authenticate using your account's supported method, grant Bedrock/discovery/STS and optional Service Quotas permissions, choose a model/region and verify its runtime quotas. Expert linguistic and cultural validation remains necessary for research-grade results.

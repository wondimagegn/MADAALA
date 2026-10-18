# EthioContextEval

EthioContextEval is a human-grounded multilingual AI evaluation pilot measuring language parity, contextual fidelity, safety consistency and robustness across English, Amharic and Afaan Oromo, designed for Ethiopian contextual evaluation.

## Research scope

The preserved dataset contains 12 scenarios ? 3 languages = 36 records across education, public services, business/finance and Ethiopian contextual reasoning. English (`en`) is a semantic control, not sufficient ground truth for cultural validity. Amharic (`am`) and Afaan Oromo (`om`) prompts are AI drafts requiring expert linguistic and cultural validation.

All current records, including English, have `pending_expert_validation`. English masters can run for feasibility testing, but **none of the current records is research grade**. Draft translations require `--allow-unvalidated`. Research grade requires ready translation metadata and `validated` or `expert_validated` validation status, independent of language. Pending outputs have `research_grade=false`, `technical_pilot=true`. Never automatically relabel drafts.

## Repository structure

```text
config/                 Bedrock example and offline mock config
 data/                  main scenarios, English subset, translation backup
 docs/                  methodology, annotation rubric, schema and ethics
 reports/               historical pilot report and cleanup verification
 scripts/               Windows/Linux AWS checks; dataset construction utility
 src/ethiocontexteval/  runner, dataset, config, models, quotas, analysis,
                        anonymization, human evaluation, metrics
   providers/           base, bedrock_provider, mock_provider
 tests/                 offline unit and pipeline tests
 results/               raw/, blinded/, ratings/, analysis/
```

## Requirements

Python 3.11+ recommended (minimum 3.10), Git, AWS CLI v2 and an AWS account with Bedrock permissions for paid runs. Mock needs no AWS. Install AWS CLI using the [official guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then run `aws --version`.

## Clone and Python environment ? Windows PowerShell

```powershell
git clone https://github.com/wondimagegn/ethiocontexteval.git
cd ethiocontexteval
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item config/models.bedrock.example.json config/models.bedrock.json
python -m ethiocontexteval.dataset validate data/scenarios.jsonl
python -m ethiocontexteval.runner --help
```

## Clone and Python environment ? Linux/bash

```bash
git clone https://github.com/wondimagegn/ethiocontexteval.git
cd ethiocontexteval
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp config/models.bedrock.example.json config/models.bedrock.json
python -m ethiocontexteval.dataset validate data/scenarios.jsonl
python -m ethiocontexteval.runner --help
```

Use `python -m pip install -e .` without development tools. AWS dependencies are included; `[aws]` remains a compatibility extra. Run commands from the clone root. The copied Bedrock config is local and ignored by Git. Replace its model ID/region with one usable by your account.

## AWS authentication

Choose one method appropriate to your account (commands work in both shells):

```text
aws configure --profile ethiocontext
```

Or browser login where available:

```text
aws login --profile ethiocontext
```

Or IAM Identity Center:

```text
aws configure sso --profile ethiocontext
aws sso login --profile ethiocontext
```

Verify identity:

```text
aws sts get-caller-identity --profile ethiocontext
```

The normal boto3 credential chain supports profiles, login/SSO, environment credentials and IAM roles. Omit `--profile` for the default chain. Never commit credentials or `.env`. Profile names and regions are safe to log; review STS account identity output before sharing.

### AWS CRT requirement

Browser login needs recent boto3 and CRT; both are included in package dependencies. Repair older installations with `python -m pip install --upgrade "boto3>=1.41.0" "botocore[crt]>=1.41.0"` (or `python -m pip install "botocore[crt]"`). See [boto3 credentials](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).

## Discovery and quota checks

PowerShell:

```powershell
.\scripts\check_aws_environment.ps1 -Profile ethiocontext -Region eu-north-1
```

Linux:

```bash
bash scripts/check_aws_environment.sh ethiocontext eu-north-1
```

Both check CLI version, STS identity and Bedrock discovery without inference. Additional read-only diagnostics:

```text
python -m ethiocontexteval.models list --provider bedrock --profile ethiocontext --region eu-north-1
python -m ethiocontexteval.models check --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json
python -m ethiocontexteval.quotas --profile ethiocontext --region eu-north-1 --search Qwen
```

Discovery compares exact foundation-model IDs and **does not establish runtime capacity**. For an independently verified inference profile absent from foundation-model discovery, use `--skip-model-check` on execution. This does not bypass AWS authorization or quotas.

In AWS Service Quotas select Amazon Bedrock and your region. Check applied RPM, TPM and daily limits for the exact model and inference mode. Zero RPM/TPM can block inference even when discovery succeeds. The quota utility paginates applied quotas without hardcoded quota IDs; name matching is advisory and does not block runs. Empty results or denied permissions mean quota remains unknown. See [AWS runtime quota guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas-runtime.html).

## First dry run

PowerShell:

```powershell
python -m ethiocontexteval.runner `
  --provider bedrock --profile ethiocontext --region eu-north-1 `
  --config config/models.bedrock.json --dataset data/scenarios.jsonl `
  --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 `
  --runs 1 --temperature 0 --max-tokens 500 --dry-run
```

Linux/bash:

```bash
python -m ethiocontexteval.runner \
  --provider bedrock --profile ethiocontext --region eu-north-1 \
  --config config/models.bedrock.json --dataset data/scenarios.jsonl \
  --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 \
  --runs 1 --temperature 0 --max-tokens 500 --dry-run
```

Expected generations: 1. No inference requests were sent. Planning is offline and does not verify AWS access. With neither execution flag, the CLI safely plans. Unknown/disabled model IDs and unknown scenario/language selections fail clearly.

## First real smoke test

**THIS COMMAND MAKES A REAL PAID BEDROCK REQUEST.** After verifying access/quota, this command works in both shells:

```text
python -m ethiocontexteval.runner --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json --dataset data/scenarios.jsonl --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 --runs 1 --temperature 0 --max-tokens 500 --execute --output results/raw/qwen_EDU001_en.jsonl
```

One generation is planned; transient failures may cause bounded retries.

## Three-language technical pilot

Reuse the dry-run command, keeping the exact scenario/model and one run. Plan separately with `--language en`, `--language am --allow-unvalidated`, and `--language om --allow-unvalidated`. Review each plan before replacing `--dry-run` with `--execute`. Choose separate output paths, e.g. `results/raw/qwen_EDU001_am.jsonl`. Draft outputs are technical only; the override prints a warning and preserves metadata.

## Full research pilot

Workflow: dataset validation ? dry run ? smoke test ? expert translation/cultural validation ? full pilot ? blinding ? independent human evaluation ? analysis. After expert validation, 12 ? 3 ? 2 models ? 2 runs = 144 generations. First configure two models and plan with `--runs 2 --dry-run`; review the count before execution. Draft overrides do not make research findings valid.

## Results and resume

JSONL rows capture response/scenario IDs, domain, language, variant, provider/model, run, temperature/max tokens, prompt/response, latency, input/output/total tokens, finish reason, timestamp, status/error, translation/validation status at run, research grade, technical-pilot flag and provider metadata. Missing token usage stays null. Failures are recorded with useful errors; rows are flushed incrementally.

Use `--resume-from results/raw/previous.jsonl --output results/raw/resumed.jsonl` to copy prior rows and skip successful `(provider, scenario, language, variant, model, run)` keys. Errors are retried. Reusing an output also skips successful keys. Keep dataset, prompts and generation settings identical: resume keys do not include prompt/settings hashes. Raw outputs/private blind mappings stay ignored. Review any artifacts before publishing.

Evaluation tools:

```text
python -m ethiocontexteval.anonymize --help
python -m ethiocontexteval.human_evaluation --help
python -m ethiocontexteval.analysis --help
```

See `docs/annotation-guidelines.md` and `docs/data-schema.md`. Historical reports describe their original run conditions, not current AWS access guarantees.

## Offline testing

These commands work in both shells without AWS requests:

```text
python -m pytest
python -m ruff check .
python -m ruff format --check src tests
python -m ethiocontexteval.dataset validate data/scenarios.jsonl
python -m ethiocontexteval.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --max-tokens 100 --dry-run
python -m ethiocontexteval.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --max-tokens 100 --execute --output results/raw/mock_smoke.jsonl
```

Mock outputs are synthetic, never experimental findings. CI runs offline checks on Windows/Linux with Python 3.11/3.12.

## Troubleshooting

- No credentials: authenticate or refresh the selected profile; omit it for IAM roles/environment credentials.
- CRT login error: upgrade boto3 and `botocore[crt]` as above.
- Access denied: ask your account administrator for required Bedrock permissions.
- Model/profile not found: check exact ID and region.
- ValidationException: inspect the actual AWS message for model/settings requirements.
- Model visible but inference fails, including ?Too many tokens per day?: verify account/model/region runtime RPM/TPM and daily quotas before assuming daily usage was exhausted. Zero quota is an AWS capacity issue.
- Unvalidated records skipped: use `--allow-unvalidated` only for technical testing. Empty prompts always stay skipped.
- Old local `.env`: remove stale Ollama provider/config overrides; Ollama is no longer supported.

## Reproducibility and ethics

Record Git commit (`git rev-parse HEAD`), dataset hash/version, exact model ID, AWS region, generation settings, runs, validation status and timestamp. Results depend on model/version/region/time and require human evaluation. Expert translation/cultural validation is essential. This small pilot cannot represent every Ethiopian cultural context or language variety. See the methodology and ethics documents.

## License

MIT; see [LICENSE](LICENSE).

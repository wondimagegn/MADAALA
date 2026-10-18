# EthioContextEval

EthioContextEval is a human-grounded multilingual AI evaluation pilot measuring language parity, contextual fidelity, safety consistency and robustness across English, Amharic and Afaan Oromo, designed for Ethiopian contextual evaluation.

## Beginner walkthrough: from clone to your first model response

This is a Python command-line application. Run commands in a terminal; there is no web interface to start. The runner sends dataset prompts to a model and saves the responses as JSONL (one JSON object per line). Complete the steps in order. Steps 1-4 work without AWS; step 8 incurs model charges.

### Step 1: install the tools and clone

Install [Python 3.11 or newer](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads). On Windows, enable Python's PATH option during installation and open a new PowerShell terminal. Do not type the terminal prompt, such as `PS D:\Project\ethiocontexteval>`, as part of a command.

```text
git clone https://github.com/wondimagegn/ethiocontexteval.git
cd ethiocontexteval
```

Already cloned? Open a terminal in that folder instead. Do not clone inside the existing repository. All following commands assume the repository root is the current directory.

### Step 2: create and activate a Python environment

Windows PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Linux/bash:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Debian/Ubuntu, if creating the environment reports missing `venv` support, install your Python version's `python3-venv` package using your system package manager. Activate the environment again whenever you open a new terminal. The installation includes the AWS SDK and test tools. `-e` means edits to the local Python source are used directly.

If Windows blocks activation, you can use `.\.venv\Scripts\python.exe` in place of `python` in subsequent commands without changing your execution policy. On Linux the equivalent is `.venv/bin/python`.

### Step 3: verify the installation and dataset

```text
python -m ethiocontexteval.runner --help
python -m ethiocontexteval.dataset validate data/scenarios.jsonl
python -m pytest
python -m ruff check .
```

Expected: 36 valid records, 12 executable by default and 24 draft records skipped; the automated tests and lint checks pass. Stop and resolve errors before paid execution. Dataset validation checks structure and metadata, not translation accuracy.

### Step 4: run a free synthetic example

These commands work unchanged in PowerShell and bash. Copy each complete line:

```text
python -m ethiocontexteval.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --max-tokens 100 --dry-run
python -m ethiocontexteval.runner --provider mock --config config/models.mock.json --scenario EDU-001 --language en --model mock-model-a --runs 1 --max-tokens 100 --execute --output results/raw/my_first_mock.jsonl
```

Expect `Expected generations: 1` from planning and `[OK]` from execution. Open `results/raw/my_first_mock.jsonl` in VS Code. The response is synthetic, not a measured model result. A second execution with the same output skips the already successful row.

### Step 5: install AWS CLI and sign in

Install [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), then check `aws --version`. For browser login you need CLI 2.32.0 or newer and the account permissions described in [AWS's login guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

If your account supports browser login:

```text
aws login --profile ethiocontext
```

For an organization using IAM Identity Center, use these instead; ask its administrator for the SSO setup details:

```text
aws configure sso --profile ethiocontext
aws sso login --profile ethiocontext
```

Then verify the selected identity:

```text
aws sts get-caller-identity --profile ethiocontext
```

`ethiocontext` is a local profile name, not a credential supplied by this repository. Authenticate to your own account. Do not paste keys into source files. The account needs Bedrock discovery and model-invocation permissions; Service Quotas diagnostics also need permission to list service quotas. See the authentication section below for other credential-chain options.

### Step 6: configure one model and check AWS access

Copy the example once. Do not overwrite a configuration you have already customized.

Windows PowerShell:

```powershell
Copy-Item config/models.bedrock.example.json config/models.bedrock.json
.\scripts\check_aws_environment.ps1 -Profile ethiocontext -Region eu-north-1
```

Linux/bash:

```bash
cp config/models.bedrock.example.json config/models.bedrock.json
bash scripts/check_aws_environment.sh ethiocontext eu-north-1
```

Open `config/models.bedrock.json` in your editor. Keep one model enabled for your first test. The example uses `qwen.qwen3-235b-a22b-2507-v1:0` in `eu-north-1` (Europe/Stockholm); replace both consistently if your account uses another supported model or region. Use the same model ID in subsequent `--model` arguments.

```text
python -m ethiocontexteval.models check --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json
python -m ethiocontexteval.quotas --profile ethiocontext --region eu-north-1 --search Qwen
```

Open the [Bedrock console](https://console.aws.amazon.com/bedrock/) and [Service Quotas console](https://console.aws.amazon.com/servicequotas/), select the same region and check the exact model's applied runtime limits. Discovery does not prove inference permission or usable quota. Follow [AWS runtime quota guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas-runtime.html) if limits are zero or requests are throttled. These checks do not invoke a model.

### Step 7: plan exactly one real-model generation

```text
python -m ethiocontexteval.runner --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json --dataset data/scenarios.jsonl --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 --runs 1 --temperature 0 --max-tokens 1000 --dry-run
```

Confirm one selected record, one selected model and one expected generation. This is an offline plan: zero inference requests and no runtime-access guarantee.

### Step 8: execute one paid generation

**This command incurs AWS inference charges.** It plans one generation; transient errors can trigger bounded retries.

```text
python -m ethiocontexteval.runner --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json --dataset data/scenarios.jsonl --scenario EDU-001 --language en --model qwen.qwen3-235b-a22b-2507-v1:0 --runs 1 --temperature 0 --max-tokens 1000 --execute --output results/raw/my_first_bedrock_en.jsonl
```

Expect `[OK]` and the saved path. Inspect the JSONL in VS Code. On PowerShell you can display key fields with:

```powershell
Get-Content results/raw/my_first_bedrock_en.jsonl | ConvertFrom-Json | Select-Object scenario_id, language, status, error, finish_reason, response, research_grade, technical_pilot
```

On Linux:

```bash
python -m json.tool --json-lines results/raw/my_first_bedrock_en.jsonl
```

Check `status`, `error`, `response` and `finish_reason`. `status=ok` means the API call succeeded, not that the answer is accurate. `finish_reason=max_tokens` means the output reached its cap and may be incomplete. Current pending validation means `research_grade=false` and `technical_pilot=true` even for English.

### Step 9: try the other languages, then plan a larger pilot

For one Amharic generation, reuse steps 7-8 with `--language am --allow-unvalidated` and output `results/raw/my_first_bedrock_am.jsonl`. For Afaan Oromo use `--language om --allow-unvalidated` and a distinct output. These drafts require independent expert review; see [translation review instructions](docs/translation-review.md) and the [paired review sheet](data/translation-review.csv).

To plan all 36 records with one model and one run:

```text
python -m ethiocontexteval.runner --provider bedrock --profile ethiocontext --region eu-north-1 --config config/models.bedrock.json --dataset data/scenarios.jsonl --model qwen.qwen3-235b-a22b-2507-v1:0 --allow-unvalidated --runs 1 --temperature 0 --max-tokens 1000 --dry-run
```

Expect 36 generations. **Only when you intend to pay for that full run**, replace `--dry-run` with `--execute --output results/raw/my_36_record_pilot.jsonl`. Do not leave the one-scenario or one-language filters in the full-run command. This remains a technical pilot, not a validated research comparison.

The [October 18 technical pilot report](reports/proposal-feasibility.md) records 36 API-success responses, including 19 that reached the 1,000-token cap. The same cap does not guarantee equivalent answer length across languages. Agree and document any revised budget before a new run; use a new output path when changing prompts or generation settings. Rerunning with the same output skips successful keys, including responses that reached the output limit.

### Step 10: prepare responses for human evaluation

After completing your own 36-record run:

```text
python -m ethiocontexteval.anonymize results/raw/my_36_record_pilot.jsonl --blinded-out results/blinded/my_pilot.csv --mapping-out results/raw/blind_mapping_my_pilot.csv
python -m ethiocontexteval.human_evaluation template results/blinded/my_pilot.csv --out results/ratings/my_pilot_reviewer1.csv
```

Give qualified reviewers the blinded responses, matching scenario prompts and [annotation guidelines](docs/annotation-guidelines.md). Keep the mapping private. Create a separate rating file for each reviewer; do not invent ratings or use blank ratings for analysis. Draft/truncated responses can be reviewed for technical issues, but formal multilingual claims require validated matched prompts and independent human scoring. Use `python -m ethiocontexteval.analysis --help` for analysis options after actual ratings exist.

Raw responses and blinded packets are local and ignored by Git. A fresh clone includes the pilot summary and review materials, but not those private/local response files. Share reviewed artifacts separately when appropriate. The proposal report includes wording supported by the completed technical pilot and states its limitations.

## Research scope

The preserved dataset contains 12 scenarios x 3 languages = 36 records across education, public services, business/finance and Ethiopian contextual reasoning. English (`en`) is a semantic control, not sufficient ground truth for cultural validity. Amharic (`am`) and Afaan Oromo (`om`) prompts are AI drafts requiring expert linguistic and cultural validation.

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

## Clone and Python environment - Windows PowerShell

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

## Clone and Python environment - Linux/bash

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

Workflow: dataset validation -> dry run -> smoke test -> expert translation/cultural validation -> full pilot -> blinding -> independent human evaluation -> analysis. After expert validation, 12 x 3 x 2 models x 2 runs = 144 generations. First configure two models and plan with `--runs 2 --dry-run`; review the count before execution. Draft overrides do not make research findings valid.

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
- Model visible but inference fails, including "Too many tokens per day": verify account/model/region runtime RPM/TPM and daily quotas before assuming daily usage was exhausted. Zero quota is an AWS capacity issue.
- Unvalidated records skipped: use `--allow-unvalidated` only for technical testing. Empty prompts always stay skipped.
- Old local `.env`: remove stale Ollama provider/config overrides; Ollama is no longer supported.

## Reproducibility and ethics

Record Git commit (`git rev-parse HEAD`), dataset hash/version, exact model ID, AWS region, generation settings, runs, validation status and timestamp. Results depend on model/version/region/time and require human evaluation. Expert translation/cultural validation is essential. This small pilot cannot represent every Ethiopian cultural context or language variety. See the methodology and ethics documents.

## License

MIT; see [LICENSE](LICENSE).

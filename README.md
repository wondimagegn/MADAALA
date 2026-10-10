# EthioContextEval Pilot

**Human-Grounded Evaluation of Multilingual Generative AI for Ethiopian Contexts**

University research prototype supporting an Amazon Research Awards proposal prepared with Addis Ababa University.

| Role | Lead |
|------|------|
| Research | Wondimagegn Desta, Department of Computer Science, Addis Ababa University |
| Evaluation & statistics | Endalkachew H. Chala, Analysis and Response Toolkit for Trust (ARTT) |

## Objective

Build a **provider-independent**, reproducible pipeline to evaluate generative AI on context-sensitive tasks relevant to Ethiopia, with **human** translation validation and **human** rating — not automatic scores alone.

## Provider modes

| Provider | Purpose |
|----------|---------|
| **mock** | Development, unit tests, GitHub Actions (synthetic text; **not** research results) |
| **ollama** | **Current feasibility pilot** — local open-weight models on Windows |
| **bedrock** | **Optional / future** — funded cloud evaluation when AWS research access is available |

> The preliminary feasibility pilot uses locally hosted open-weight generative models through Ollama. EthioContextEval is designed as a provider-independent evaluation framework. Amazon Bedrock integration is maintained as an optional provider and is planned for the funded study, subject to research infrastructure and AWS access.

**Do not** state that AWS Bedrock or Amazon Nova was used in the pilot unless `results/raw/` generations actually record that provider.

## Research questions (pilot)

1. Can we run a matched evaluation cell (scenario × language × model × run) with full provenance, independent of cloud vendor?
2. How do selected **local** open-weight models behave on Ethiopian-context tasks in **English** (masters), with Amharic and Afaan Oromo gated until expert translation?
3. What parity gaps and error types appear under blinded human evaluation?

## Languages

| Code | Language | Pilot status |
|------|----------|--------------|
| `en` | English | 12 master scenarios (executable) |
| `am` | Amharic | Template only — **human translation pending** |
| `om` | Afaan Oromo | Template only — **human translation pending** |

**Do not** treat machine translation as validated ground truth.

## Pilot versus full study

| | Feasibility pilot (now) | Full EthioContextEval |
|--|-------------------------|------------------------|
| Compute | Local Ollama (no AWS required) | May add Bedrock / other providers |
| Scenarios | 12 masters | Expanded bank + variants |
| Languages | EN executable; AM/OM pending | Expert-validated EN/AM/OM |
| Statistics | Descriptive, LPG, bootstrap, Wilcoxon (exploratory) | Mixed-effects, powered design |
| Claims | Tooling & methodology readiness | Scientific benchmark claims |

**No experimental results should be interpreted until human validation is completed.**

## Methodology (summary)

1. Author English master scenarios (education, public services, business/finance, Ethiopian contextual reasoning).
2. Validate JSONL; block untranslated prompts.
3. Select provider (`mock` / `ollama` / `bedrock`); health-check; verify models (**no auto-download** for Ollama).
4. Generate with normalized result schema; write JSONL incrementally.
5. Blind responses (hide provider + model id).
6. Human ratings (1–5 + error codes).
7. Metrics/statistics/report from **real** artifacts only.

Details: [`docs/methodology.md`](docs/methodology.md), [`docs/pilot-protocol.md`](docs/pilot-protocol.md).

## Repository structure

```
config/                 models.local.json (Ollama), models.example.json (Bedrock optional), models.mock.json
data/                   Scenario JSONL
docs/                   Methodology, schema, ethics, guidelines
src/ethiocontexteval/
  providers/            base, mock, ollama, bedrock
  ...                   dataset, runner, anonymize, metrics, analysis
scripts/                check_environment.ps1, run_local_pilot.ps1
tests/                  pytest (no cloud / no live Ollama required)
```

## Windows setup

```powershell
git clone https://github.com/wondimagegn/ethiocontexteval.git
cd ethiocontexteval

python -m venv .venv
# If activation is blocked (session only):
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Optional future AWS extras (not required for local pilot):

```powershell
pip install -e ".[aws]"
```

### Ollama (local pilot)

1. Install Ollama for Windows from the official distribution.
2. Ensure the local API is available at `http://localhost:11434` (default).
3. **Manually** pull candidate models if needed, for example:
   ```powershell
   ollama pull qwen2.5:7b
   ollama pull gemma3:4b
   ```
   On limited hardware consider `qwen2.5:3b`, `llama3.2:3b`, or `gemma3:4b`.
4. This repository **does not** auto-download models and makes **no** claim that candidates perform well on Amharic or Afaan Oromo.

```powershell
.\scripts\check_environment.ps1
python -m ethiocontexteval.models health --provider ollama
python -m ethiocontexteval.models list --provider ollama
```

### Optional Amazon Bedrock (funded path)

```powershell
pip install -e ".[aws]"
aws configure   # or IAM role; never commit keys
python -m ethiocontexteval.models list --provider bedrock
```

## Tests

```powershell
pytest -m "not integration"
ruff check src tests
```

CI uses **MockProvider** only — no Ollama, no AWS, no secrets.

## Dataset validation

```powershell
python -m ethiocontexteval.dataset validate data\scenarios.jsonl
python -m ethiocontexteval.dataset summary data\scenarios.jsonl
```

## Dry run (no inference)

```powershell
python -m ethiocontexteval.runner --provider ollama --config config\models.local.json --dry-run
# CI / offline:
python -m ethiocontexteval.runner --provider mock --config config\models.mock.json --dry-run
```

Default local plan (when two models enabled): **12 × 2 × 2 = 48** generations (English only).

## Execute local pilot (explicit confirmation)

```powershell
.\scripts\run_local_pilot.ps1
# or:
python -m ethiocontexteval.runner --provider ollama --config config\models.local.json --execute
```

## Anonymization, rating, analysis

```powershell
python -m ethiocontexteval.anonymize results\raw\generations_TIMESTAMP.jsonl
python -m ethiocontexteval.human_evaluation template results\blinded\blinded_responses_TIMESTAMP.csv
python -m ethiocontexteval.analysis --report-only-template
python -m ethiocontexteval.analysis path\to\ratings.csv --mapping results\raw\blind_mapping_TIMESTAMP.csv
```

## Responsible AI

- No credentials in repository
- No fabricated Amharic/Oromo translations or results
- Blinded human evaluation (provider-blind)
- Mock outputs never presented as experimental findings
- Clear pilot limitations in analysis/report paths

See [`docs/ethics-and-data-governance.md`](docs/ethics-and-data-governance.md).

## License

MIT — see [`LICENSE`](LICENSE).

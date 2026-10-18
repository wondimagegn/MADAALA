> Current workflow: Bedrock is the research provider; mock is for offline tests. Ollama references below are historical. Current Amharic/Afaan Oromo prompts are AI drafts requiring validation. Use README.md for current commands and safeguards.

# Pilot Protocol

## Scope

Technical and methodological readiness pilot for EthioContextEval.

- 12 English master scenarios
- Multilingual template with `am`/`om` pending human translation
- Up to 2 **local** candidate models × 2 runs (Ollama)
- Human ratings after blinding
- Bedrock retained as **optional future** provider (not required now)

## Preconditions

1. Python 3.10+ venv with package installed (`pip install -e ".[dev]"`)
2. Dataset validates
3. **For local pilot:** Ollama installed, daemon running, candidate models pulled **manually**
4. **For future Bedrock:** `pip install -e ".[aws]"`, AWS credentials, Bedrock model access

## Steps (local Ollama)

### 1. Environment check

```powershell
.\scripts\check_environment.ps1
```

### 2. Validate data

```powershell
python -m ethiocontexteval.dataset validate data\scenarios.jsonl
```

### 3. Provider health and models

```powershell
python -m ethiocontexteval.models health --provider ollama
python -m ethiocontexteval.models list --provider ollama
python -m ethiocontexteval.models check --provider ollama --config config\models.local.json
```

### 4. Dry run (mandatory before inference)

```powershell
python -m ethiocontexteval.runner --provider ollama --config config\models.local.json --dry-run
```

### 5. Execute generations (explicit only)

```powershell
.\scripts\run_local_pilot.ps1
# or:
python -m ethiocontexteval.runner --provider ollama --config config\models.local.json --execute
```

### 6. Anonymize / rate / analyze

Same as before: `anonymize` → human_evaluation template → fill ratings → `analysis`.

## Mock / CI

```powershell
python -m ethiocontexteval.runner --provider mock --config config\models.mock.json --dry-run
```

## Optional future Bedrock

```powershell
pip install -e ".[aws]"
python -m ethiocontexteval.models list --provider bedrock
python -m ethiocontexteval.runner --provider bedrock --config config\models.example.json --dry-run
```

Only claim Bedrock usage when generations JSONL records `provider: "bedrock"`.

## Stop conditions

- Stop if dataset invalid
- Stop if provider unhealthy or models missing
- Do not auto-download large models
- Do not publish blind mappings
- Do not interpret results before human validation
- Do not treat mock outputs as experimental findings

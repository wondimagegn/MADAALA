# Pilot Protocol

## Scope

Technical and methodological readiness pilot for EthioContextEval.

- 12 English master scenarios
- Multilingual template with `am`/`om` pending
- Up to 2 Bedrock models × 2 runs
- Human ratings after blinding

## Preconditions

1. Python 3.10+ venv with package installed
2. Dataset validates
3. AWS credentials configured via CLI/env/role (not in repo)
4. Bedrock model access in the chosen region verified

## Steps

### 1. Environment check

```powershell
.\scripts\check_environment.ps1
```

### 2. Validate data

```powershell
python -m ethiocontexteval.dataset validate data\scenarios.jsonl
```

### 3. Discover models

```powershell
python -m ethiocontexteval.models list
python -m ethiocontexteval.models check
```

### 4. Dry run (mandatory before paid calls)

```powershell
python -m ethiocontexteval.runner --dry-run
```

Confirm expected API request count.

### 5. Execute generations (explicit only)

```powershell
python -m ethiocontexteval.runner --execute
```

Or use `.\scripts\run_pilot.ps1` which requires confirmation.

### 6. Anonymize

```powershell
python -m ethiocontexteval.anonymize results\raw\generations_TIMESTAMP.jsonl
```

### 7. Rating template

```powershell
python -m ethiocontexteval.human_evaluation template results\blinded\blinded_responses_TIMESTAMP.csv
```

### 8. Analyze (after ratings exist)

```powershell
python -m ethiocontexteval.analysis path\to\ratings.csv --mapping results\raw\blind_mapping_TIMESTAMP.csv
```

### 9. Template report anytime

```powershell
python -m ethiocontexteval.analysis --report-only-template
```

## Stop conditions

- Stop if dataset invalid
- Stop if models unavailable in region
- Stop if cost/rate limits exceeded
- Do not publish blind mappings
- Do not interpret results before human validation

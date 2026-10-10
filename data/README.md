# Data

## Files

| File | Purpose |
|------|---------|
| `pilot_scenarios_en.jsonl` | Twelve English **master** scenarios for the technical pilot |
| `scenarios.jsonl` | Multilingual working set (`en` / `am` / `om`) |

## Languages

- **en** — English masters (executable when `translation_status=master_english`)
- **am** — Amharic (prompt `null` until **human** translation + expert validation)
- **om** — Afaan Oromo (same policy)

**Do not** insert machine-translated text into `am`/`om` prompts and treat it as validated ground truth.

## Domains (12 masters)

| IDs | Domain |
|-----|--------|
| EDU-001 … EDU-003 | Education |
| GOV-001 … GOV-003 | Public services |
| BUS-001 … BUS-003 | Business / finance |
| CTX-001 … CTX-003 | Ethiopian contextual reasoning |

## Validation

```powershell
python -m ethiocontexteval.dataset validate data/scenarios.jsonl
python -m ethiocontexteval.dataset summary data/scenarios.jsonl
```

Executable pilot cells currently are English-only until translations are completed.

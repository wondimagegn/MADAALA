# Data Schema

## Scenario JSONL (`data/*.jsonl`)

Each line is one JSON object.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `scenario_id` | string | yes | e.g., `EDU-001` |
| `domain` | string | yes | `education`, `public_services`, `business_finance`, `ethiopian_contextual_reasoning` |
| `difficulty` | int | yes | 1–5 |
| `language` | string | yes | `en`, `am`, `om` |
| `variant` | string | yes | default `standard` |
| `prompt` | string or null | yes | null if untranslated |
| `expected_behavior` | string[] | yes | nonempty |
| `cultural_dependency` | bool | yes | |
| `safety_sensitive` | bool | yes | |
| `translation_status` | string | yes | e.g. `master_english`, `pending_human_translation` |
| `validation_status` | string | yes | e.g. `pending_expert_validation` |
| `source_language` | string | recommended | usually `en` |
| `linguistic_validator` | string/null | optional | |
| `cultural_validator` | string/null | optional | |
| `validation_notes` | string/null | optional | |

**Uniqueness:** `(scenario_id, language, variant)` must be unique.

**Executability:** A record is sent to models only if it has a nonempty prompt and a ready translation status (English `master_english` is ready; `am`/`om` require human-translated/validated statuses). AI drafts may have nonempty prompts but require --allow-unvalidated for technical testing. Research grade additionally requires validated/expert_validated validation status.

## Generation JSONL (`results/raw/generations_*.jsonl`)

| Field | Type |
|-------|------|
| `response_id` | UUID string |
| `scenario_id` | string |
| `domain` | string |
| `language` | string |
| `variant` | string |
| `provider` | string (`mock` \| `ollama` \| `bedrock`) |
| `model_id` | string |
| `model_name` | string |
| `run` | int |
| `temperature` | number |
| `max_tokens` | int |
| `prompt` | string |
| `response` | string/null |
| `latency_seconds` | number/null |
| `input_tokens` | int/null |
| `output_tokens` | int/null |
| `total_tokens` | int/null |
| `finish_reason` | string/null |
| `timestamp` | ISO-8601 |
| `error` | string/null |
| `status` | `ok` \| `error` |
| `provider_metadata` | object |

## Blinded CSV (`results/blinded/blinded_responses_*.csv`)

`blind_id, scenario_id, domain, language, variant, run, response`  
**No** model fields.

## Private mapping (`results/raw/blind_mapping_*.csv`)

`blind_id, response_id, provider, model_id, model_name, scenario_id, language, run`  
**Do not publish.**

## Ratings CSV (`results/ratings/*.csv`)

See `human_evaluation.TEMPLATE_FIELDS` and `docs/annotation-guidelines.md`.

Generation rows preserve translation_status_at_run, validation_status_at_run, research_grade and technical_pilot.

# EthioContextEval Pilot

## Objective

Assess the feasibility of human-grounded evaluation of multilingual generative AI for Ethiopian contexts (English, Amharic, Afaan Oromo), supporting the broader EthioContextEval research program and Amazon Research Awards proposal readiness.

## Research Question

How do selected generative models behave on matched, context-sensitive tasks across English, Amharic, and Afaan Oromo, as judged by human evaluators on correctness, context fidelity, instruction following, language quality, usefulness, and safety?

## Experimental Design

- **Languages:** English (master), Amharic and Afaan Oromo (human translation pending).
- **Domains:** education, public services, business/finance, Ethiopian contextual reasoning.
- **Design cell:** scenarios × languages × models × repeated generations.
- **Inference:** Amazon Bedrock Converse API; temperature 0 by default.
- **Blinding:** evaluators see responses without model identity.

## Dataset

Twelve English master scenarios (`data/pilot_scenarios_en.jsonl`), expanded to a multilingual template (`data/scenarios.jsonl`) with Amharic and Afaan Oromo prompts left null until expert translation and validation. **No machine translation is treated as ground truth.**

## Models

- `nova-lite`: `amazon.nova-lite-v1:0` (enabled)
- `nova-pro`: `amazon.nova-pro-v1:0` (enabled)

Model availability must be verified per region via `python -m ethiocontexteval.models list`.

## Human Evaluation

Independent raters score blinded responses on 1–5 Likert dimensions (see `docs/annotation-guidelines.md`). Error codes E1–E10 may be applied.

## Statistical Methodology

Descriptive means by language/model/domain; Language Parity Gap (LPG) and Normalized LPG; bootstrap confidence intervals; Wilcoxon signed-rank on paired English–target language scores when pairs suffice; Krippendorff's alpha for multi-rater agreement. **Mixed-effects models are reserved for the full study.**

> WARNING: This is a feasibility pilot with a small scenario set (n~12 masters). Statistical power is limited. Do not generalize results to all generative AI models or to all Ethiopian language varieties. Human expert validation of translations and ratings is required before scientific interpretation.

## Preliminary Results

_No human ratings are available yet. This section is a template only. Do not invent or impute experimental results._

## Error Analysis

_Pending ratings with error codes (E1–E10)._

## Limitations

- Small pilot scenario count (12 masters).
- Amharic and Afaan Oromo prompts require expert translation before multilingual claims.
- Limited statistical power; p-values are exploratory.
- Model availability and behavior vary by AWS region and time.
- Single-institution pilot evaluators may not represent all user communities.

## Lessons Learned

_To be completed after the first end-to-end pilot cycle (generation → blinding → rating → analysis)._

## Implications for Full EthioContextEval Study

The pilot validates tooling, schema, blinding, and analysis pathways. The full study should expand scenario coverage, complete human translation and cultural validation, increase rater diversity, and apply mixed-effects models for crossed scenario/language/model factors.

## Reproducibility

- Configuration via environment variables and `config/models*.json`.
- Dataset validation: `python -m ethiocontexteval.dataset validate`.
- Dry run: `python -m ethiocontexteval.runner --dry-run`.
- Tests: `pytest`.
- No AWS credentials are stored in the repository.

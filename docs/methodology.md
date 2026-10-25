# MADAALA methodology

MADAALA evaluates whether matched user intents receive comparably accurate, actionable, contextually appropriate and safe responses in English, Amharic and Afaan Oromo. English is a comparison condition, not cultural ground truth.

## Study design

The proposed benchmark contains about 500 matched scenarios across seven domains and three difficulty levels. Language specialists will author each language realization from a shared scenario specification, followed by bilingual validation. Need-finding in Addis Ababa and Adama informs the user intents. See the [implementation roadmap](madaala-roadmap.md) for the full design and delivery targets.

The current dataset contains 12 scenarios across four domains, with 36 prompt records. Amharic and Afaan Oromo prompts are AI-assisted drafts. All records, including English, are pending expert validation. Default execution selects 12 English records for technical testing; `--allow-unvalidated` includes draft target-language records. Neither option establishes research validity.

## Providers and generation

| Provider | Current role |
|---|---|
| `bedrock` | Real model generation through AWS; inference incurs charges |
| `mock` | Synthetic responses for offline development and CI |

SageMaker adapters and suitable Bedrock model imports are planned extensions. The implemented pipeline uses the same scenario schema, normalized response records, blinding and rating tools across supported providers.

1. Author and validate matched prompts, recording provenance and review decisions.
2. Validate dataset structure and execution eligibility.
3. Select exact models and check discovery, permissions and quotas.
4. Plan a bounded run with `--dry-run` before using `--execute`.
5. Generate responses with recorded settings and validation snapshots.
6. Export blinded responses while keeping identity mappings private.
7. Collect independent qualified human ratings.
8. Analyze actual scores and report completion, exclusions and uncertainty.

Generation count is `selected records ? selected models ? runs`. A 12-scenario, three-language, two-model, two-run prototype experiment produces 144 planned generations. This is separate from the expanded benchmark design.

Equal token caps can cause unequal completion rates across languages. Calibrate budgets before production, preserve truncation as an outcome and use a new output path whenever prompts or settings change. Resume keys do not include prompt or settings hashes.

## Human evaluation

The current [annotation guidelines](annotation-guidelines.md) define the implemented rating fields. Formal multilingual comparisons require validated matched prompts and independent human ratings. Blank templates and mock outputs cannot support quality claims.

The proposed study expands the rubric to factual correctness, instruction preservation, language quality, actionability, contextual fidelity, cultural appropriateness, tone and dignity, and safety or refusal appropriateness. A stratified core of about 150 scenarios for six models will receive two ratings per response, with calibration, disagreement preservation and adjudication.

## Analysis

The primary planned measure is paired Language Parity Gap per model and dimension: `score(English) - score(target language)`. Positive values indicate a higher English score. The proposed analysis uses scenario-clustered bootstrap confidence intervals, dimensional reporting, mixed-effects models and prespecified multiplicity adjustments. Robustness, fabricated-premise and safety probes are analyzed separately.

Current utilities provide score summaries, composite helpers, gap calculations and pilot statistical tools. They do not implement the complete proposed analysis or calibrated automated judging. Automated scoring will extend only to language-by-dimension combinations validated against held-out human ratings; safety-critical judgments retain qualified human review.

## Available evidence

The [18 October 2026 feasibility pilot](../reports/proposal-feasibility.md) produced 36 successful Bedrock responses from one model and one run; 19 reached the 1,000-token output cap. Prompts lack independent expert validation and responses lack human scoring. These results establish technical feasibility only.

Use the [pilot protocol](pilot-protocol.md) for executable commands and the [ethics guidance](ethics-and-data-governance.md) for data handling.

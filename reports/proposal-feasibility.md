# Proposal feasibility pilot - 2026-10-18

## Actual Bedrock results

Completed the authorized 36 generations: 12 scenarios, three languages, one model and one run. All 36 returned API-success rows. **19/36 responses reached the 1,000-output-token limit.** API success is not a quality score; output-limit responses may be incomplete.

| Language | Records | API successes | Output-limit responses | Mean latency (s) | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|---:|
| en | 12 | 12 | 0 | 6.62 | 941 | 7622 |
| am | 12 | 12 | 10 | 9.57 | 4308 | 11004 |
| om | 12 | 12 | 9 | 9.05 | 2537 | 9839 |

Model: `qwen.qwen3-235b-a22b-2507-v1:0`. Region: eu-north-1. Temperature: 0. Maximum output tokens: 1000. All outputs remain technical pilots: validation metadata is pending expert validation, including English. Timestamp interval (UTC): 2026-10-18T09:52:38.982066+00:00 to 2026-10-18T09:57:41.255784+00:00. No additional paid replacement generations were run.

## Proposal-ready wording

"We implemented and exercised a multilingual evaluation pipeline covering 12 Ethiopian-context scenarios in English, Amharic and Afaan Oromo. A preliminary Amazon Bedrock technical pilot with Qwen3-235B produced 36 API-success responses, one per scenario-language pair, using temperature 0 and a maximum of 1,000 output tokens. Of these, 19 reached the configured output limit. These results establish technical execution feasibility under the tested configuration, rather than validated multilingual performance. Independent linguistic and cultural validation of draft prompts, human evaluation of responses, and investigation of language-dependent output-budget requirements are planned before comparative performance claims."

## Illustrative issue requiring human review

EDU-001 Amharic appears to introduce specific clock times that were not supplied in the prompt. EDU-001 Afaan Oromo reached the output limit. These are unscored observations to inspect with qualified reviewers, not adjudicated findings or error-rate estimates. No human scores, language-parity metrics or significance tests were invented.

## Translation preparation

All 24 target-language prompts already contain AI-assisted drafts. Dataset prompts were preserved for this pilot; no expert validation has been claimed. The review sheet pairs English and target prompts and leaves reviewer decisions blank. See docs/translation-review.md for specific wording issues and review instructions.

## Artifacts

- reports/proposal-pilot-summary.json: counts, configuration, timestamps, dataset/output hashes and source Git commit.
- data/translation-review.csv: 24 paired translation review records.
- results/raw/proposal_bedrock_20261018.jsonl: 36 actual Bedrock responses (local, ignored by Git).
- results/blinded/proposal_bedrock_20261018.csv: blinded responses for technical review.
- results/raw/blind_mapping_proposal_20261018.csv: private model mapping; do not share with blinded reviewers.
- results/ratings/proposal_20261018_blank.csv: unfilled rating template; create separate copies per reviewer.
- results/analysis/proposal_technical_review.csv: per-response technical completion and truncation inventory.
- results/raw/proposal_mock_pipeline.jsonl: separate synthetic offline test; excluded from real-model summary.

## Limits and next steps

Single model, one run, small scenario set, draft translations, incomplete responses and no independent human ratings. The same output-token cap does not ensure equivalent answer length across languages. Neither API completion nor differing token counts establishes language quality or parity. Costs were not estimated; consult AWS billing for actual charges.

Obtain independent prompt review, then have qualified reviewers inspect complete and truncated responses with the rubric. Keep technical-review scores separate from formal validated results. Agree a revised generation budget before any further paid run. Automated tests: 31 passed; structural dataset validation: 36 valid records. No commits were made for this pilot preparation.

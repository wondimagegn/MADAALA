# Ethics and Data Governance

## Principles

- **Human grounding first.** Model outputs are research artifacts, not authoritative advice for legal, medical, or identity procedures.
- **No fabricated multilingual ground truth.** Amharic and Afaan Oromo prompts require human translation and expert validation.
- **Minimize sensitive data.** Scenarios use placeholders; do not collect real national ID numbers, OTPs, or private citizen data in prompts or logs.
- **Blinding.** Human raters should not see model identity during scoring.
- **Credential hygiene.** AWS keys, GitHub tokens, and `.env` secrets never enter git.
- **Honest reporting.** No invented metrics, translations, or experimental results.

## Public vs private artifacts

| Publishable | Keep private / local |
|-------------|----------------------|
| English master scenarios | `.env`, AWS credentials |
| Docs, code, tests | `results/raw/blind_mapping_*.csv` |
| Aggregated analysis tables after review | Raw generations if they contain sensitive user content (pilot uses synthetic prompts) |
| Blinded sheets (without mapping) | Individual rater identity beyond coded evaluator_id if required by IRB |

## Safety-sensitive scenarios

When `safety_sensitive=true`, raters should complete the safety dimension. Models must not be used to solicit secrets (PINs, OTPs).

## Institutional context

Pilot supporting research at Addis Ababa University and collaborators (including ARTT evaluation/statistics). Align additional IRB or data-sharing agreements with university policy before expanding beyond synthetic pilot prompts.

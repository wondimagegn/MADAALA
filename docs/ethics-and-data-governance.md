# MADAALA ethics and data governance

## Principles

- **Human grounding first.** Model outputs are research artifacts, not authoritative advice for legal, medical, or identity procedures.
- **No fabricated multilingual ground truth.** All language realizations require qualified linguistic and cultural validation. The proposed benchmark uses local authoring from shared intent specifications; current AI-assisted drafts require independent review.
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

The MADAALA proposal identifies Addis Ababa University as project lead and ethics-review institution. Participant recruitment, interviews and use of newly elicited participant data require applicable approval. Participant transcripts remain on AAU systems; only de-identified scenario text enters AWS. Planned release follows responsible-release review, with sensitive metadata and fabricated-program probes assessed for restricted access. See the [roadmap](madaala-roadmap.md) for proposed responsibilities and deliverables.

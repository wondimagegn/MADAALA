# Methodology — EthioContextEval Pilot

## Goal

Demonstrate a reproducible, human-grounded pipeline for evaluating generative AI on Ethiopian-context tasks in English, Amharic, and Afaan Oromo.

## Design cell

\[
N_{\text{responses}} \le N_{\text{scenarios}} \times N_{\text{languages}} \times N_{\text{models}} \times N_{\text{runs}}
\]

Pilot target: **12 × 3 × 2 × 2 = 144** (when translations exist).  
**Current executable subset:** English masters only → **12 × 1 × 2 × 2 = 48** Bedrock calls with default config.

## Pipeline stages

1. **Scenario authoring** (English masters; expert translation later)
2. **Dataset validation** (schema, executability gates)
3. **Model discovery** (Bedrock `ListFoundationModels`)
4. **Generation** (Bedrock Runtime `Converse`, temperature 0 default)
5. **Blinding** (strip model identity for raters)
6. **Independent human rating** (1–5 dimensions + error codes)
7. **Metrics & statistics** (parity gaps, bootstrap CIs, Wilcoxon where appropriate)
8. **Reporting** (only from actual artifacts; no fabricated results)

## Human grounding

Automatic scores are **not** treated as final scientific outcomes. Human evaluation is required before interpreting model quality, especially for Amharic and Afaan Oromo.

## Statistics (pilot)

- Descriptive means by language / model / domain
- Language Parity Gap: \(LPG_l = S_{en} - S_l\)
- Normalized LPG: \(NLPG_l = (S_{en} - S_l)/S_{en}\) (undefined if \(S_{en}=0\))
- Bootstrap 95% CIs
- Wilcoxon signed-rank on matched pairs when \(n \ge 6\)
- Krippendorff’s α for multi-rater agreement

**Warning:** \(n=12\) masters is a feasibility pilot. Power is limited. Do not generalize.

## Full study extension points

- Larger scenario bank and variants (robustness)
- Completed human translations + linguistic/cultural validators
- Mixed-effects models (scenario × language × model)
- Broader rater pools and adjudication

# Methodology — EthioContextEval Pilot

## Goal

Demonstrate a reproducible, human-grounded pipeline for evaluating generative AI on Ethiopian-context tasks in English, Amharic, and Afaan Oromo.

## Scientific object

The object of evaluation is **model behavior**, not the hosting platform.

```
Local open-weight model  ──┐
                           ├──► EthioContextEval protocol ──► Human evaluation
Cloud / Bedrock model    ──┘              │
                                          ▼
                              Language-parity metrics
                                          │
                                          ▼
                               Statistical analysis
```

The same dataset schema, blinding, rating dimensions, parity metrics, and statistical procedures apply regardless of whether generation used **Ollama (local)** or **Amazon Bedrock (optional future / funded path)**.

## Provider modes

| Mode | Role |
|------|------|
| **Mock** | CI, unit tests, offline development (synthetic text; **not** research results) |
| **Ollama** | Current **feasibility pilot** on Windows without cloud billing |
| **Bedrock** | Optional provider retained for a **funded** cloud study when AWS research access is available |

The preliminary feasibility pilot uses locally hosted open-weight generative models through Ollama. EthioContextEval is designed as a provider-independent evaluation framework. Amazon Bedrock integration is maintained as an optional provider and is planned for the funded study, subject to research infrastructure and AWS access.

**Do not** describe the pilot as having used Bedrock or Amazon Nova unless those backends were actually executed and logged in `results/raw/`.

## Design cell

\[
N_{\text{responses}} \le N_{\text{scenarios}} \times N_{\text{languages}} \times N_{\text{models}} \times N_{\text{runs}}
\]

Pilot target when translations exist: **12 × 3 × 2 × 2 = 144**.  
**Current executable subset:** English masters only → **12 × 1 × 2 × 2 = 48** generations with default two-model local config.

## Pipeline stages

1. **Scenario authoring** (English masters; expert translation later)
2. **Dataset validation** (schema, executability gates)
3. **Provider health + model discovery** (Ollama tags / Bedrock list / mock catalog)
4. **Generation** via `ModelProvider.generate` (default temperature `0`)
5. **Blinding** (strip provider + model identity for raters)
6. **Independent human rating** (1–5 dimensions + error codes E1–E10)
7. **Metrics & statistics** (parity gaps, bootstrap CIs, Wilcoxon where appropriate)
8. **Reporting** (only from actual artifacts; no fabricated results)

## Human grounding

Automatic scores are **not** final scientific outcomes. Human evaluation is required before interpreting model quality, especially for Amharic and Afaan Oromo. Multilingual parity gaps are **not** computed as study findings until validated multilingual ratings exist.

## Statistics (pilot)

- Descriptive means by language / model / domain
- Language Parity Gap: \(LPG_l = S_{en} - S_l\)
- Normalized LPG: \(NLPG_l = (S_{en} - S_l)/S_{en}\) (undefined if \(S_{en}=0\))
- Context Fidelity Gap, Safety Consistency Gap, Robustness Gap (variants)
- Bootstrap 95% CIs
- Wilcoxon signed-rank on matched pairs when \(n \ge 6\)
- Krippendorff’s α for multi-rater agreement

**Warning:** \(n=12\) masters is a feasibility pilot. Power is limited. Do not generalize.

## Full study extension points

- Larger scenario bank and variants (robustness)
- Completed human translations + linguistic/cultural validators
- Optional Bedrock (or other cloud) providers under the same protocol
- Mixed-effects models (scenario × language × model)
- Broader rater pools and adjudication

# MADAALA methodology

This document follows the research questions and approach in the MADAALA proposal. The study described below is planned research; the final section identifies the current implementation and available evidence.

## Research questions

1. Holding user intent constant, how do correctness, usefulness, context fidelity, dignity and safety differ between English and Amharic or Afaan Oromo*
2. Under what linguistic, institutional and safety conditions do disparities widen*
3. To what extent do rubric-driven automated judges reproduce qualified native-speaker judgments across languages and dimensions*

## Matched-scenario design

The unit of analysis is a matched scenario set: one specified user intent, an English control, and independently validated Amharic and Afaan Oromo prompts that preserve intent while allowing culturally appropriate expression. English is a comparison condition, not a source text or cultural ground truth. The within-item design reduces, but does not remove, confounding between language and item difficulty.

About **500 scenarios / 1,500 primary prompts** will cover three difficulty levels across seven domains:

- Education.
- Public administration.
- Financial and small-business services.
- Digital services.
- Everyday information seeking.
- Culturally dependent reasoning.
- Safety-sensitive interactions.

## Need-finding and local-first construction

Six to eight structured sessions with about 30 participants in Addis Ababa and Adama (Nazret) will identify real information needs, local terminology and communication conventions. Participants will include Amharic and Afaan Oromo speakers with experience in education, local administration, health information, financial services and small business. Recruitment seeks variation in language use rather than assigning one language to each city.

Language specialists will write all three realizations from a shared scenario specification. Bilingual reviewers will check semantic equivalence and record cases where exact alignment would distort the request. Each scenario will carry domain, difficulty, intended goal, contextual dependencies, expected response, safety considerations and provenance metadata. A pilot of **80-100 scenarios** will test clarity, comparability and annotation feasibility before full construction.

Participant engagement and use of newly elicited participant data require applicable ethics approval. See the [ethics and data-governance guidance](ethics-and-data-governance.md).

## Targeted probe families

Three probe sets will be analyzed separately from primary scores.

| Probe family | Design and purpose |
|---|---|
| Linguistic robustness | Compare standard prompts with Latin-script transliteration of Amharic, spelling variants, informal register, regional lexical variation in Qubee Afaan Oromo and English code-switching. |
| Fabricated premises | About 40 scenarios involving plausible but fictitious institutions, policies or programs. Verify them against available sources at construction time and check for real-entity name collisions in all three languages. Assess whether models flag unsupported premises or fabricate authoritative-sounding detail. |
| Safety consistency | About 60 scenarios across health, legal and administrative procedure, finance and digital security, combining requests needing qualification with requests warranting refusal. Assess preservation of essential safety information, warranted refusal and local feasibility. |

A refusal in one language is not automatically inconsistent. Evaluation depends on the request, the safety concern and the adequacy of the response.

## Model selection and screening

Evaluate **8-10 systems**: foundation models available through Amazon Bedrock, plus open-weight multilingual and Amharic- or Afaan Oromo-adapted models deployed on Amazon SageMaker AI or imported into Bedrock where architecture, format and licensing permit.

Every candidate will undergo a prespecified smoke test reviewed by proficient speakers, covering prompt comprehension, requested-language generation, script handling, instruction preservation and completion reliability. Weak systems remain in the coverage audit; exclusions from numerical comparisons must be documented. Screening items are withheld from subsequent analyses.

## Controlled generation

Every model will receive the same scenario intent through the three validated prompts under standardized instructions, randomized order and a frozen evaluation-set version. Run records will include:

- Model identity and revision, provider and region.
- System message and full request and response.
- Decoding settings and token limits.
- Latency, token usage and safety-block indicators.
- Code commit.

A calibration set will fix a prespecified output budget per interface. Equal token ceilings can yield unequal completion rates because tokenization and output length vary by model and language. Truncation and completion will be reported as outcomes rather than hidden as missing data. API failures, missing-language responses and content filters will be logged, with retry rules applied identically across languages.

Model outputs will be stripped of identifying information before human evaluation; private model mappings remain separate from reviewer packets.

## Native-speaker human evaluation

A stratified core of about **150 scenarios**, spanning domains, difficulties and probes, will anchor human judgment. Six models will be selected to span provider type and language adaptation. Trained raters will use masked model identifiers and a shared handbook to score:

- Factual correctness.
- Instruction preservation.
- Language quality.
- Actionability.
- Contextual fidelity.
- Cultural appropriateness.
- Tone and dignity.
- Safety or refusal appropriateness.

Raters will work in English-Amharic and English-Afaan Oromo language pairs, with two raters per item and adjudication on disagreement. The planning ceiling is `150 scenarios * 3 languages * 6 models * 2 raters = 5,400` response-level ratings before adjudication and calibration. Annotation allocation will be reassessed using pilot-measured time per rating and supervision costs.

Before production, a calibration round will estimate inter-rater reliability by language and construct. Disagreement will be preserved rather than averaged away. The remaining 2-4 models may receive exploratory automated scoring where judge validity is independently established; these results will be distinguished from human-rated comparisons and will not be presented as evidentially equivalent.

## Automated judging and calibration

A Bedrock-hosted judge will apply the same rubric. On the 150-scenario core, measure judge-human agreement separately by language, dimension and model, including detection of disparities flagged by humans and expression of uncertainty. The proposal anticipates weaker agreement in Amharic and Afaan Oromo; this is an expectation to test, not an established result. Documenting judge failures is a deliverable.

Automated scoring will extend to the remaining approximately **350 scenarios** only for language-by-dimension combinations meeting prespecified agreement thresholds on held-out human-rated data. Checks will address systematic bias and detection of cross-language disparities. Fix judge-use thresholds for each language and dimension before production analysis. Scoring outside validated combinations remains explicitly exploratory. Safety-critical judgments retain qualified human review.

## Measures and statistical analysis

The primary estimand is the paired **Language Parity Gap** per dimension and model:

```text
LPG = score(English) - score(target language)
```

Positive values indicate a higher English score. Aggregate gaps over matched scenarios with bootstrap confidence intervals clustered by scenario.

Secondary measures include factual-grounding error, instruction preservation, robustness drop, over-refusal, safety-consistency gap, completion and latency. Stratify results by model, language, domain, difficulty and probe type. No composite leaderboard score replaces dimensional reporting.

Ordinal and binary outcomes will use mixed-effects models with scenario and rater effects. The stratified human-evaluation core supports matched-gap estimation with uncertainty intervals. Simulation-based power and precision analyses will use pilot estimates of within-scenario variation, rater disagreement and model effects to inform final rating allocation and interpretation of subgroup contrasts. Apply multiplicity adjustments to prespecified contrast families.

## Current implementation and feasibility evidence

The current MADAALA dataset contains **12 scenarios across four domains / 36 prompt records**. Amharic and Afaan Oromo prompts are AI-assisted drafts; all records, including English, are pending expert validation. Default execution selects 12 English records for technical testing; `--allow-unvalidated` includes draft target-language records. These execution settings do not establish research validity.

The implemented providers are `bedrock` for real AWS inference and `mock` for synthetic offline development. SageMaker adapters, the expanded rubric, randomized versioned run manifests, calibrated judging and the full proposed statistical analysis remain implementation work. Current utilities provide blinded exports, rating templates, score summaries, composite helpers, gap calculations and pilot statistical tools. The [annotation guidelines](annotation-guidelines.md) describe the implemented rubric, which must be expanded for the proposed study.

The [18 October 2026 feasibility pilot](../reports/proposal-feasibility.md) produced 36 successful Bedrock responses from one model and one run; 19 reached the 1,000-token output cap. These establish technical feasibility only and motivate output-budget calibration; they do not establish model quality or language parity. Blank ratings and mock outputs cannot support research conclusions.

Use the [pilot protocol](pilot-protocol.md) for executable commands and the [implementation roadmap](madaala-roadmap.md) for delivery targets. Preserve completed experiments and use fresh output paths when prompts or settings change; current resume keys do not include prompt or settings hashes.

# MADAALA proposal alignment and implementation roadmap

This roadmap summarizes the MADAALA research proposal dated 21 October 2026, **MADAALA: A Human-Grounded Benchmark for Language Parity in Amharic and Afaan Oromo**. It distinguishes proposed research from the existing MADAALA prototype. The proposal remains a working draft with eligibility, budget and personnel confirmation pending.

## Research design

The unit of analysis is a matched scenario set expressing one user intent in English, Amharic and Afaan Oromo. Language specialists will author each realization from a shared specification, then bilingual reviewers will validate equivalence and document unavoidable differences. English is a comparison condition. The current pilot contains English master prompts and AI-assisted translations. The proposed benchmark uses independently authored language realizations.

Need-finding will involve six to eight structured sessions with about 30 participants in Addis Ababa and Adama, seeking variation in language use and service experience. A pilot of 80–100 scenarios will precede a bank of about 500 scenarios at three difficulty levels across seven domains: education; public administration; financial and small-business services; digital services; everyday information seeking; culturally dependent reasoning; and safety-sensitive interactions.

Metadata will record intent, domain, difficulty, contextual dependencies, expected response, safety considerations and provenance. Robustness variants include Amharic transliteration, spelling and register variation, regional Qubee vocabulary and English code-switching. Approximately 40 fabricated-premise scenarios require source verification and multilingual name-collision checks; approximately 60 safety scenarios assess qualification, warranted refusal, essential safety information and local feasibility. Probe families are analyzed separately from primary scores.

## Model runs and human grounding

Screen 8–10 candidate systems for comprehension, requested-language generation, script handling, instruction preservation and completion reliability. Screening prompts stay outside subsequent analyses. Retain weak systems in a coverage audit and document exclusions. Proposed hosting includes Bedrock, SageMaker AI and supported Bedrock model import, subject to licensing and technical compatibility.

Freeze evaluation versions, standardize instructions, randomize request order and record full run manifests. Calibrate output budgets per interface before production because equal token caps can produce unequal completion rates. Record truncation, API failures, missing-language responses, content filters and identical retry rules across languages as outcomes.

A stratified core of about 150 scenarios will receive blinded native-speaker evaluation for six models, with two raters per response in English–Amharic and English–Afaan Oromo language pairs. The planning ceiling is `150 × 3 × 6 × 2 = 5,400` response-level ratings before adjudication and calibration. Pilot-measured annotation time and supervision costs must inform final allocation. Preserve disagreement and adjudication records and estimate reliability by language and construct.

The proposed rubric includes factual correctness, instruction preservation, language quality, actionability, contextual fidelity, cultural appropriateness, tone and dignity, and safety or refusal appropriateness. These constructs require a revised handbook and schema beyond the prototype's current fields.

A Bedrock-hosted automated judge must be tested against held-out human ratings separately by language, dimension and model, including disparity detection, uncertainty and systematic bias. Fix use thresholds before production analysis. Extend scoring to the remaining approximately 350 scenarios only in validated language-by-dimension combinations. Other scores, including coverage of the remaining 2–4 models, are exploratory and distinct from human-rated comparisons. Safety-critical judgments retain qualified human review.

## Analysis to implement

The primary estimand is paired Language Parity Gap per model and dimension: `LPG = score(English) − score(target language)`. Positive values indicate a higher English score. Aggregate matched scenarios with bootstrap confidence intervals clustered by scenario. Report dimensions individually, with strata for language, model, domain, difficulty and probe type.

Secondary outcomes include factual-grounding error, instruction preservation, robustness drop, over-refusal, safety-consistency gap, completion and latency. Proposed ordinal and binary analyses use mixed-effects models with scenario and rater effects. Pilot-informed simulation will guide power, precision and rating allocation; prespecified contrast families require multiplicity adjustment. A composite leaderboard does not replace dimensional reporting.

## Implementation gaps

| Area | Available prototype | Work required for the revised proposal |
|---|---|---|
| Scenarios | 12 scenarios / 36 records, all pending expert validation | Locally authored matched-intent bank, richer metadata, secure versioning, probe taxonomy and validation records |
| Providers | Bedrock and offline mock | Suitable SageMaker adapters, screening audit, documented deployment configurations |
| Generation | Filtering, dry runs, JSONL logging, bounded retries and resume | Randomization, frozen manifests, calibrated budgets, explicit filter outcomes and stronger experiment identity |
| Human evaluation | Blinded CSV export, private mapping, rating templates and prototype rubric | Expanded rubric, rater calibration, paired assignment, adjudication and disagreement preservation |
| Automated judging | No calibrated judge workflow | Rubric judge, held-out calibration, language/dimension thresholds and bias/disparity checks |
| Analysis | Pilot summaries, composite helpers and existing statistical utilities | Matched dimension-specific estimates, scenario-clustered intervals, mixed effects, multiplicity and power simulations |
| Release | Public code and technical-pilot summaries | Madaala v1.0, MadaalaKit v1.0, dataset/model cards, calibration data, release review and training materials |

The [technical feasibility report](../reports/proposal-feasibility.md) documents 36 API-success responses, including 19 at the output limit. Prompts lack independent expert validation and responses lack human scoring. These establish pipeline feasibility only. Preserve this experiment and use separate versioned outputs for the new study. The [methodology](methodology.md) distinguishes the implemented pilot workflow from the proposed study design.

## Proposed delivery sequence

Months are relative to award notification, not repository release dates.

| Period | Planned work |
|---|---|
| Months 1–2 | Ethics submission, appoint language leads, finalize need-finding protocol/taxonomy, provision AWS and draft rubric |
| Months 2–3 | Approved need-finding, transcription and synthesis |
| Months 3–4 | Scenario pilot, coverage screening, output-budget and annotation calibration |
| Months 4–6 | Full construction, bilingual validation, release-safe metadata and MadaalaKit alpha |
| Months 7–9 | Model runs, human evaluation, judge calibration and probe evaluation |
| Months 10–11 | Analysis, uncertainty/sensitivity checks and paper draft |
| Month 12 | Reviewed open release, technical report, AAU workshop and sustainability plan |

## Governance and release

The proposal identifies Addis Ababa University as project lead and ethics-review institution, with language specialists responsible for validation and adjudication. Participant recruitment, interviews and use of newly elicited participant data require applicable ethics approval. Preparatory software work can proceed before approval.

Participant transcripts remain on AAU systems; only de-identified scenario text enters AWS. Planned S3 storage needs versioning and role-based access. Select regions after checking model availability, costs, quotas and approved data handling. Code and releasable data are intended for GitHub and Hugging Face under permissive licenses following responsible-release review; fabricated-program probes and sensitive metadata may require gating. The current repository's MIT license does not establish licensing for future participant-derived data or model checkpoints.

PI eligibility, institutional contracting, personnel, annotation costs, power/precision assumptions, judge thresholds and final infrastructure choices remain to be confirmed. Planned deliverables and partnerships should not be presented as completed releases or confirmed awards.

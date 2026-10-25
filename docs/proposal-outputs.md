# MADAALA outputs for proposal writing and analysis

## Available now: the technical feasibility pilot

These artifacts describe the 36-generation MADAALA Bedrock feasibility run. No human-scored performance analysis is available yet.

| Artifact | Purpose | Included in a fresh clone? |
|---|---|---|
| [Proposal feasibility report](../reports/proposal-feasibility.md) | Verified completion/truncation table, proposal wording and limitations | Yes |
| [Pilot summary JSON](../reports/proposal-pilot-summary.json) | Model/settings, timestamps, dataset/output hashes and per-language totals | Yes |
| [Technical inventory CSV](../results/analysis/proposal_technical_review.csv) | Per-response status, finish reason, tokens and latency | Yes |
| [Translation review CSV](../data/translation-review.csv) | 24 paired prompts for independent review; decisions blank | Yes |
| [Blank rating template](../results/ratings/proposal_20261018_blank.csv) | Empty human score sheet, not completed ratings | Yes |
| results/raw/proposal_bedrock_20261018.jsonl | Actual generated response text and metadata | No: local/ignored |
| results/blinded/proposal_bedrock_20261018.csv | Blinded response packet for reviewers | No: local/ignored |
| results/raw/blind_mapping_proposal_20261018.csv | Private mapping from blind IDs to model identity | No: keep private |

Start proposal writing from the feasibility report, not reports/pilot_report.md, which is a report template. The pilot produced 36 API-success rows and 19 output-limit responses (English 0, Amharic 10, Afaan Oromo 9). This demonstrates technical execution with the tested settings, not validated language quality. The mock output is synthetic and excluded from this evidence.

## After human translation and a new model run

Save revised prompts, actual review metadata, dataset commit/hash and the new run's configuration. Use new output paths so the old run is not overwritten or accidentally resumed. Recompute completion, errors and truncation from that new run; do not reuse the old summary numbers.

Prepare blinded responses and independent rating templates using README steps 9-10. Have qualified reviewers complete separate files, preserving blind IDs and distinct evaluator IDs. Before analysis, review missing scores, matching scenario-language pairs, evaluator agreement, technical-only metadata and incomplete responses. Document any exclusions instead of silently dropping records.

When actual ratings exist, this example command analyzes them (replace filenames with the filled files):

```text
python -m madaala.analysis results/ratings/reviewer1_filled.csv results/ratings/reviewer2_filled.csv --mapping results/raw/blind_mapping_validated_pilot_v2.csv
```

The CLI writes tables under results/analysis/: language_scores.csv, domain_scores.csv, parity_gaps.csv, error_counts.csv and summary.csv. Applicable figures go under results/analysis/figures/. Its Markdown report goes to reports/pilot_report.md. These default locations may overwrite a previous analysis. Review the report's template narrative and replace it with facts from the actual experiment before using it in a proposal.

For separate output directories, use the Python API, for example:

```python
from pathlib import Path
from madaala.analysis import run_analysis_pipeline

run_analysis_pipeline(
    [Path("results/ratings/reviewer1_filled.csv"),
     Path("results/ratings/reviewer2_filled.csv")],
    mapping_path=Path("results/raw/blind_mapping_validated_pilot_v2.csv"),
    analysis_dir=Path("results/analysis/validated_pilot_v2"),
    report_path=Path("reports/validated_pilot_v2.md"),
)
```

Do not execute this example until the real filled inputs exist. No scores or performance conclusions should be generated from blank templates. Present the first run as infrastructure feasibility, and the reviewed rerun as a separate experiment. Changes to both prompts and token budgets mean differences cannot be attributed solely to translation improvements.

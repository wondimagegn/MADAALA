# Translation review for the proposal pilot

All 24 Amharic/Afaan Oromo prompts already contain AI-assisted draft translations. Open data/translation-review.csv with UTF-8 support. It pairs English and draft prompts with the unchanged evaluation criteria. Blank reviewer fields are intentional; no human review has been claimed.

Independent fluent reviewers should check semantic equivalence, all numbers and time constraints, safety instructions, naturalness/register and cultural appropriateness. Record proposed corrections, reviewer identities and decisions. Prioritize:

- GOV-001 Amharic: the literal rendering of "high-level overview" may suggest hierarchy rather than a general overview.
- CTX-002 Amharic: the rendering of "address practices" may suggest physical addresses rather than forms of addressing people.
- EDU-002 Afaan Oromo: confirm "in six weeks" is expressed as six weeks from now, not an interval within which exams start.
- Review administrative terminology, formative/summative assessment, cash flow and calendar month names across the full set.

These are AI editorial observations, not expert findings. The dataset remains unchanged in this preparation step. Shared English expected_behavior fields are evaluator criteria, not model input requiring translation.

Keep translation_status=ai_draft_translation and validation_status=pending_expert_validation until review is completed. Do not automatically supply validator identities or approvals. Version prompt edits and obtain review before formal comparison.

For the proposal, draft-language runs are technical feasibility evidence. Language-parity and safety-quality conclusions require validated matched prompts and independent human ratings. One model and one run cannot establish comparative performance.

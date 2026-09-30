# Complete Project Index

## Current handoff

The current source of truth is [CURRENT_STATUS.md](CURRENT_STATUS.md). The original `v1/` tree is preserved and its dated status pages are historical. The new `v1_1/` package is an engineering/research candidate; it is not automatically promoted over the old provisional reference.

| Need | Location |
|---|---|
| Acceptance and no-promotion decision | `v1_1/docs/RELEASE_DECISION.md` and `.pdf` |
| Reviewer overview | `v1_1/docs/REVIEWER_BRIEF.html` |
| Detailed report, limitations and source references | `v1_1/docs/TECHNICAL_CLOSEOUT.md` |
| Editable / printable executive report | `v1_1/docs/EXECUTIVE_HANDOFF.docx` / `.pdf` |
| Five-minute demonstration | `v1_1/docs/DEMO_SCRIPT.md` |
| Invocation / handlers / security / rollback | `v1_1/docs/INTEGRATION.md` |
| Original requirements and contributor provenance | `v1_1/docs/SOURCE_REGISTER.md` |
| Rebuild and run | `v1_1/README.md`, `requirements.txt`, `Makefile`, `Dockerfile` |
| Frozen modeling protocol | `v1_1/config/protocol.json` |
| Unknown deployment and cost inputs | `v1_1/config/deployment.example.json`, `cost_model.example.json` |
| Received review, untouched | `v1_1/data/manual_review_received.csv` |
| Review decisions, disagreements and exclusions | `v1_1/artifacts/data/review_audit.csv`, `review_summary.json`, `deferred_context.csv` |
| Strict training and family exclusions | `v1_1/artifacts/data/training_strict.csv`, `excluded_benchmark_families.csv`, `integrity.json` |
| Training-only selection | `v1_1/artifacts/selection.json`, `oof_policy_comparison.csv`, model OOF exports |
| Historical benchmark candidate predictions/errors | `v1_1/artifacts/models/*/benchmark/` |
| Core/stress applicability and failures | `v1_1/artifacts/applicability/` |
| Candidate runtime artifact | `v1_1/artifacts/release/` |
| Unit, HTTP, Docker, load and contract proof | `v1_1/artifacts/verification/`, `FINAL_VALIDATION.json` |
| Machine-readable summary and delivery boundaries | `v1_1/artifacts/SUMMARY.json`, `COMPLETION_MATRIX.json`, `RELEASE_DECISION.json` |
| File integrity | `v1_1/artifacts/SHA256SUMS.json` |

## Repository structure

```text
README.md                 Current overview and measured comparison
CURRENT_STATUS.md         Engineering/quality/deployment separation
PROJECT_INDEX.md          This map
v1_1/                     Executed closeout, new candidate and handoff
v1/                       Preserved original query-only release and evidence
Part 1 - Phases 6 and 7/   Original contributor datasets and experiments
Part 2 - Step 3/          Original persona/intent validation package
research_archive/         Explicitly separate historical experimental report
.github/workflows/        Original V1 and closeout verification workflows
```

## Historical work and interpretation

The original phase plan and documents are the basis for source/requirements traceability. Its broader persona/intent scope was narrowed by the later team decision to the four-route query-only contract. Original private/confidential drafts are not newly republished.

`Part 1 - Phases 6 and 7/` contains raw CSV contributors and early modeling, including the old strict grouped-query result 0.816829. `Part 2 - Step 3/` contains the early evaluation/export framework; mock outputs are illustrative and not performance evidence.

`research_archive/2026-08-30-hardcore-v1/` records a separate smaller-data 552-case experiment. Its 93.30% hybrid headline is not the result of this closeout, not comparable to the current training protocol, and not a production guarantee. No unverified chat-only V1.2 claims are promoted into the current release.

## Issues

- [#1](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/1): original Qwen comparison contribution.
- [#2](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2): review submission and audited dispositions.
- [#3](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3): applicability execution, including failed cases and independence limitation.
- [#4](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/4): completed product-scope review.
- [#5](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5): external architecture/data/approval gate; remains open.

## Evidence rules

Never silently replace an old benchmark, overwrite a contributor's opinion, claim assistant-authored tests are independent, equate a green build with model acceptance, or substitute unknown infrastructure costs with zero. Exact/family de-duplication is a heuristic guard, not a guarantee of semantic independence. Further model development needs a new declared evaluation protocol, not retrospective benchmark tuning.

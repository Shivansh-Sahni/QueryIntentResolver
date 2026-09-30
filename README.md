# Query Intent Resolver

**Engineering closeout delivered. Model-quality and live-deployment gates remain explicit.**

A query-only routing component for MascotGO: raw text in, one handling route and its confidence out. This repository contains the original contributor work, the preserved V1.0.1 reference, and the new V1.1 engineering/research handoff with executed evidence.

```json
{"route":"complex","confidence":0.91}
```

The four routes remain `short_circuit`, `medium`, `complex`, and `llm_needed`. Persona, page, filters, context and session are optional but do not affect predictions. The resolver does not execute a downstream action.

## Start here

| Purpose | File |
|---|---|
| Current decision and status | [CURRENT_STATUS.md](CURRENT_STATUS.md) |
| One-page release decision | [Release decision PDF](v1_1/docs/RELEASE_DECISION.pdf) |
| Reviewer dashboard | [Reviewer brief HTML](v1_1/docs/REVIEWER_BRIEF.html) — download/open locally |
| Complete technical review | [Technical closeout](v1_1/docs/TECHNICAL_CLOSEOUT.md) |
| Printable / editable handoff | [PDF](v1_1/docs/EXECUTIVE_HANDOFF.pdf) · [DOCX](v1_1/docs/EXECUTIVE_HANDOFF.docx) |
| Run the implementation | [V1.1 README](v1_1/README.md) |
| Exact executed evidence | [SUMMARY.json](v1_1/artifacts/SUMMARY.json) · [final validation](v1_1/artifacts/FINAL_VALIDATION.json) |
| Full repository map and history | [PROJECT_INDEX.md](PROJECT_INDEX.md) |

## Release decision: no automatic promotion

V1.1 is a research and integration candidate, **not an automatic replacement for V1.0.1**. The stricter V1.1 pipeline improves evaluation hygiene and completes missing engineering work, but it fails the unchanged short-circuit safety requirement. A higher accuracy point estimate does not compensate for unsafe routing.

| System / evaluation set | Accuracy | Macro F1 | False short circuits / predicted short circuits | Short-circuit recall |
|---|---:|---:|---:|---:|
| Preserved V1.0.1, historical 300 queries | 78.00% | 0.7784 | 2/42 = 4.76% | 53.33% |
| V1.1, same historical 300 queries | 80.33% | 0.8041 | 9/62 = 14.52% | 70.67% |
| V1.1, new 100-case core applicability suite | 62.00% | 0.6175 | 4/20 = 20.00% | 64.00% |

V1.1 was chosen from three fixed candidates using grouped training-only out-of-fold results. Its training conditions differ from V1.0.1: 845 rows from heuristic template families appearing in the historical benchmark were excluded. The old benchmark has been observed previously, so it is regression evidence, not a new blind test. The paired accuracy-gain interval spans zero. The applicability suite is assistant-authored, not independent real-user validation. Twenty stress cases are reported separately.

Retain V1.0.1 as the safer **historical point-estimate reference**, still provisional because it misses the recall target. Neither version is authorized for live traffic. Full denominators, uncertainty, failures and boundaries are in the report.

## What was finished

- Received peer review: all 55 IDs verified; 15 labels retained, 30 separately AI-policy-adjudicated, 10 context-dependent rows deliberately excluded. Original submission and attribution preserved.
- Versioned reviewed pool: 7,916 rows; strict V1.1 fit: 7,071 rows with zero exact and zero declared heuristic template-family overlap with the regression benchmark.
- Three fixed lightweight model families; full text pipeline fitted inside grouped calibration folds; model and routing policy fixed before evaluation labels were read.
- 100 balanced core diagnostic cases plus 20 boundary cases; all predictions, failures, overlap audits and metamorphic checks retained.
- 42 unit tests; 134 runtime checks; actual local HTTP smoke test; actual Docker build and container inference.
- Query-only Python library, CLI, FastAPI, batch endpoint, OpenAPI export, explicit handler bindings and unbound production preflight.
- All original `v1/` files preserved byte-for-byte. New evidence is under `v1_1/`.

## Local demonstration

```bash
python -m pip install -r v1_1/requirements.txt
PYTHONPATH=v1_1 python -m qir_release "colleges in California"
PYTHONPATH=v1_1 uvicorn qir_release.api:app --host 127.0.0.1 --port 8000
```

For a complete rebuild, follow [v1_1/README.md](v1_1/README.md). Use the pinned Python environment; model files are trusted joblib artifacts, not safe arbitrary uploads. No credentials, external API calls or actual handler URLs are required for the local demo.

## Completion boundary

The standalone code, review processing, model comparisons, applicability execution and engineering handoff are delivered. The production-quality objective is not met by V1.1. Actual MascotGO handlers, index coverage, approved deployment architecture, independently labeled real queries and risk acceptance remain necessary. [Issue #5](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5) is the product-integration decision record. A successful workflow is not deployment approval.

Historical Phase 6/7, Step 3 and experimental work remain available for provenance. Older status files inside `v1/` are historical snapshots, not the current status. Archived headline metrics are not substituted for current evidence.

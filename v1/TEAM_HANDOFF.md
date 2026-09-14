# Query Intent Resolver V1 Team Handoff

## What is frozen

- Goal: predict route complexity, not persona.
- Required model input: raw query text only.
- Required public output: route plus confidence.
- Route labels: `short_circuit`, `medium`, `complex`, `llm_needed`.
- Benchmark seed: `20260830`.
- Frozen benchmark: 300 balanced queries, 75 per route.
- Final MascotGO and Foundry binding: configurable pending architecture confirmation.

The live project state is recorded in [`CURRENT_STATUS.md`](./CURRENT_STATUS.md). The September 2 status file is retained only as a historical checkpoint.

## What runs now

```bash
python v1/scripts/run_v1_pipeline.py
```

The pipeline performs:

- label cleanup and conflict auditing;
- immutable benchmark verification;
- supervised model training;
- deterministic diagnostic evaluation;
- preservation and scoring of committed external Qwen predictions;
- safety-first model comparison;
- release packaging;
- runtime and hash validation.

Current artifacts report:

- 8,171 cleaned unique queries;
- 55 unresolved unique queries isolated for review;
- 7,871 training queries after benchmark exclusion;
- zero exact-query train/benchmark leakage;
- two verified real model evaluations: calibrated LinearSVC and Qwen transfer;
- validated Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces.

## Files to review first

1. `v1/CURRENT_STATUS.md`
2. `v1/artifacts/VALIDATION_REPORT.json`
3. `v1/artifacts/shootout/SHOOTOUT_REPORT.md`
4. `v1/artifacts/release/release_manifest.json`
5. `v1/artifacts/data_cleanup/manual_review_queue.csv`
6. `v1/artifacts/models/linearsvc/REPORT.md`
7. `v1/artifacts/models/qwen/REPORT.md`

## Active ownership

### Shivansh — technical coordinator, integration, and final release

Deliverable: the final reproducible V1 recommendation and MascotGO integration handoff.

- preserve the frozen contract and benchmark;
- maintain CI, API, documentation, validation, and release artifacts;
- integrate reviewed label decisions through the audit-preserving merge path;
- analyze natural-query failures;
- obtain route bindings, available context, real-query validation access, and deployment decisions from Peter;
- open a versioned V1.1 effort only after the current evidence is complete.

### Nimisha — unresolved-label adjudication

Deliverable: completed review decisions for the 55 quarantined unique queries.

- use `v1/artifacts/data_cleanup/manual_review_queue.csv`;
- apply the definitions in `ROUTING_LABEL_POLICY.md`;
- record proposed route, one-sentence rationale, confidence, and reviewer name;
- flag context-dependent examples rather than forcing certainty;
- do not edit or relabel the frozen benchmark.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2

### Ridhi — primary natural-query and API applicability test

Deliverable: a test log covering at least 25 naturally phrased queries.

- run the API or CLI;
- cover all four route classes;
- include typos, shorthand, incomplete wording, and conversational phrasing;
- record expected route, actual route, confidence, pass/fail, and issue note;
- verify that successful API output remains exactly `{route, confidence}`;
- report failures without correcting them after prediction.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3

### Anika — independent reviewer and issue #3 backup

- review the expected labels assigned in Ridhi's test;
- independently examine failed and borderline cases;
- complete the primary test if Ridhi is unavailable;
- do not add observed test examples to the frozen benchmark.

### Tanvi — product-scope review completed

Tanvi confirmed that the V1 objective and four route labels match the current product scope. She identified the downstream route bindings as the remaining product requirement. Issue #4 is complete and closed.

### Anthony — Qwen comparison completed

Anthony completed inference for all 300 blind benchmark rows. The raw export is preserved and scored without post-hoc intent reparsing or benchmark-driven tuning.

Qwen result:

- Accuracy: 27.33%
- Macro F1: 0.1771
- False short-circuit rate: 16.67%
- Short-circuit recall: 6.67%
- P95 latency: approximately 4,151 ms/query

The current persona/intent model is not suitable for the four-route V1 task. Issue #1 is complete and closed. No rerun is currently required.

### Edward — removed from active ownership

Edward has not been active in the project for approximately three months. His applicability-testing task has been reassigned to Ridhi, with Anika as independent reviewer and backup.

## Peter integration decisions

The remaining product decisions are:

1. Which surfaces invoke the resolver first: search bar, chat, GO button, or all?
2. What concrete downstream service corresponds to each route?
3. Which optional context fields can the application supply reliably?
4. Can a privacy-safe real-query sample or shadow-mode feed be provided?
5. Should the resolver deploy as a standalone service, backend module, or Foundry action?

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5

## API

```bash
PYTHONPATH=v1/src uvicorn qir_v1.api:app --host 0.0.0.0 --port 8000
```

Request:

```bash
curl -X POST http://localhost:8000/v1/resolve \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"UCLA vs USC for engineering"}'
```

Response:

```json
{
  "route": "complex",
  "confidence": 0.91
}
```

## Guardrails

- Never edit or relabel the frozen benchmark after viewing predictions.
- Never tune a model, prompt, generation setting, or parser against frozen-benchmark errors.
- Never present mock or simulated outputs as real performance.
- Never select on headline accuracy alone; false short-circuiting is release-critical.
- Never package a diagnostic model as the release recommendation.
- Any material label-policy, route-semantics, or benchmark change requires a new version.

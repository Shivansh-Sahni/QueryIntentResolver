# Query Intent Resolver V1 Team Handoff

## What is frozen

- Goal: predict route complexity, not persona.
- Required model input: raw query text only.
- Required public output: route plus confidence.
- Route labels: `short_circuit`, `medium`, `complex`, `llm_needed`.
- Benchmark seed: `20260830`.
- Frozen benchmark: 300 balanced queries, 75 per route.
- Final MascotGO and Foundry binding: configurable pending architecture confirmation.

The complete current status and verified metrics are recorded in [`PROJECT_STATUS_2026-09-02.md`](./PROJECT_STATUS_2026-09-02.md).

## What runs now

```bash
python v1/scripts/run_v1_pipeline.py
```

This performs label cleanup, benchmark verification/freeze, LinearSVC training, evaluation, model comparison, release packaging, sample inference, and integrity checks.

The committed artifacts report:

- 8,171 cleaned unique queries;
- 55 unresolved unique queries isolated for review;
- 7,871 training rows after benchmark exclusion;
- zero exact-query train/benchmark leakage;
- validated Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces.

## Files to review first

1. `v1/PROJECT_STATUS_2026-09-02.md`
2. `v1/artifacts/VALIDATION_REPORT.json`
3. `v1/artifacts/data_cleanup/cleanup_summary.json`
4. `v1/artifacts/data_cleanup/manual_review_queue.csv`
5. `v1/artifacts/benchmark/benchmark_manifest.json`
6. `v1/artifacts/models/linearsvc/REPORT.md`
7. `v1/artifacts/shootout/SHOOTOUT_REPORT.md`
8. `v1/artifacts/release/release_manifest.json`

## Active ownership

### Shivansh — technical coordinator and final integration

Deliverable: one final, reproducible V1 recommendation and integration-ready release.

- preserve the frozen contract and benchmark;
- coordinate the shared model comparison;
- score incoming prediction exports;
- incorporate reviewed label decisions through the audit-preserving merge path;
- maintain the resolver/API, documentation, validation, and release bundle;
- translate Peter's architecture decisions into concrete route bindings.

### Anthony — Qwen route benchmark

Deliverable: one valid Qwen prediction export on the frozen blind input.

```bash
python v1/scripts/run_qwen_benchmark.py \
  --input v1/artifacts/benchmark/qwen_benchmark_input.csv \
  --output v1/artifacts/models/qwen/predictions.csv
```

Then score it without modifying or using the gold benchmark during inference:

```bash
python v1/scripts/score_prediction_export.py \
  --benchmark v1/artifacts/benchmark/benchmark_gold.csv \
  --predictions v1/artifacts/models/qwen/predictions.csv \
  --output-dir v1/artifacts/models/qwen \
  --model-name anthony_qwen2_5_3b_lora_intent_to_route
```

Required output fields: benchmark ID, predicted route, confidence, predicted intent/persona, raw response, model name, latency, and parse validity. Do not tune against benchmark errors.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/1

### Tanvi — independent label adjudication

Deliverable: completed review decisions for the 55 quarantined unique queries.

- use `v1/artifacts/data_cleanup/manual_review_queue.csv`;
- apply only the definitions in `ROUTING_LABEL_POLICY.md`;
- record proposed route plus a short rationale;
- flag context-dependent examples rather than forcing certainty;
- do not edit the frozen benchmark.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2

### Edward — runtime and applicability testing

Deliverable: a short test log covering at least 25 naturally phrased queries.

- run the API or CLI;
- cover all four route classes;
- include typos, shorthand, incomplete wording, and conversational phrasing;
- record expected route, actual route, confidence, and any issue;
- verify that the public response remains exactly `{route, confidence}`.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3

### Nimisha — product-scope review

Deliverable: confirmation that the frozen V1 objective and route classes still match the intended project outcome, plus any missing product requirement.

- review the project status and integration questions;
- flag any mismatch before route bindings are finalized;
- keep project decisions synchronized across contributors.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/4

### Ridhi and Anika

No blocking task is assigned while prior leave or availability constraints remain relevant. Either may contribute an independent test or label review when available.

## Peter integration decisions

The technical pipeline is no longer blocked by model implementation. The remaining product decisions are:

1. Which surfaces invoke the resolver first: search bar, chat, GO button, or all?
2. What concrete downstream service corresponds to each of the four route labels?
3. Which optional context fields can the application supply reliably?
4. Can a privacy-safe set of real queries be provided for shadow evaluation?
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

- Never edit the frozen benchmark after viewing predictions.
- Never tune a model directly against benchmark errors.
- Never present mock or adapted outputs as real model performance.
- Never select on headline accuracy alone; false short-circuiting is release-critical.
- Any material label-policy, route-semantics, or benchmark change requires a new version.

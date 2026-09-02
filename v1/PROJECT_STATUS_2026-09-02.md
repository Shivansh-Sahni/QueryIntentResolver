# Query Intent Resolver V1 — Project Status

**Updated:** September 2, 2026  
**Current technical coordinator:** Shivansh Sahni  
**Active release:** `qir-v1.0.1`  
**Benchmark:** `qir-v1.0.0`, frozen and immutable

## Frozen product contract

V1 answers one operational question:

> Given raw query text, what minimum handling and routing tier is required?

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

Raw query text is the only required V1 model input. Persona, page, active filters, prior messages, and session context remain optional and decoupled until MascotGO confirms which fields are available.

## Completed implementation

The repository contains an end-to-end reproducible system for:

- normalizing and auditing all six contributed datasets;
- resolving contradictory historical labels conservatively;
- quarantining unresolved labels instead of guessing;
- freezing a balanced, immutable held-out benchmark;
- preventing exact-query leakage between training and evaluation;
- training a calibrated query-only routing classifier;
- evaluating deterministic, learned, Qwen-adapter, zero-shot, and API-LLM tracks under one contract;
- measuring accuracy, macro F1, false short-circuit rate, short-circuit recall, latency, confidence, and estimated cost;
- packaging the recommended real model behind Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces;
- validating hashes, runtime output, optional-context decoupling, blind-Qwen input integrity, and release-model eligibility;
- running the entire build, test, evaluation, release, artifact-upload, and artifact-commit path in GitHub Actions.

The obsolete one-time bootstrap workflow has been removed. The remaining production workflow is configured to avoid unnecessary documentation-triggered model builds and safely rebases generated-artifact commits when another commit lands during a run.

## Verified current evidence

### Data and benchmark

- Raw contributed rows: **11,575**
- Unique normalized queries: **8,226**
- Cleaned and resolved unique queries: **8,171**
- Unresolved unique queries quarantined for review: **55**
- Historical conflicting unique queries detected before resolution: **164**
- Invalid historical route rows isolated: **308**
- Training queries after benchmark exclusion: **7,871**
- Frozen benchmark: **300 queries**
- Benchmark balance: **75 queries per route class**
- Exact normalized-query train/benchmark leakage: **0**
- Manual-review-to-training leakage: **0**
- Qwen blind-input gold-label leakage: **false**
- Runtime contract validation: **passed**
- Release and benchmark hash validation: **passed**

### Current recommended real model

The current recommendation is the calibrated word/character/query-shape LinearSVC with a safety policy applied to low-confidence and unsafe short-circuit predictions.

- Accuracy: **78.0%**
- Macro F1: **0.7784**
- False short-circuit rate: **4.76%**
- Short-circuit precision: **95.24%**
- Short-circuit recall: **53.33%**
- P95 local inference latency: approximately **4.86 ms/query**
- Marginal local inference API cost: **$0**

This model passes the frozen core-quality floors and the maximum false-short-circuit ceiling, but it does not yet pass the frozen minimum short-circuit-recall requirement. It is therefore classified as **provisional safe**, not final.

### Diagnostic analytical leader

An unfiltered diagnostic variant reached:

- Accuracy: **84.0%**
- Macro F1: **0.8402**
- False short-circuit rate: **15.28%**
- Short-circuit recall: **81.33%**

It is not release-eligible. The higher headline accuracy does not compensate for routing too many non-simple queries into the cheap path. The model-selection and validation code now explicitly prevents diagnostic entries from being recommended or packaged.

### Current automation status

The latest GitHub Actions run completed successfully. It passed:

- dependency installation;
- **15 automated tests**;
- data cleanup and conflict auditing;
- immutable benchmark verification;
- model training and evaluation;
- safety-first model comparison;
- release packaging;
- artifact validation;
- release artifact upload;
- generated-artifact commit and push.

The earlier red workflow notification was caused by a non-fast-forward failure at the final generated-artifact push after another commit landed during the long run. The models, tests, validation, and artifact upload in that run had succeeded. The workflow has now been hardened with fetch/rebase/retry logic, and the replacement run passed completely.

## Current status

**Implementation complete; current release is a provisional integration candidate.**

The codebase can be demonstrated and reviewed now. Final model selection and production readiness still require:

1. the Qwen comparison on the unchanged frozen benchmark;
2. independent review of the remaining 55 unresolved labels;
3. natural-query and API applicability testing;
4. product-scope confirmation;
5. a privacy-safe real-query or shadow-mode validation set;
6. MascotGO route bindings and deployment-boundary decisions.

The current corpus is largely generated and curated, not sampled from live MascotGO traffic. Current metrics are valid for the committed frozen benchmark but should not be represented as guaranteed production performance.

## Immediate parallel workstreams

### Shivansh — technical integration and final release

- preserve the V1 contract and frozen benchmark;
- coordinate and score every model export on the same benchmark;
- incorporate reviewed label decisions through the auditable merge script;
- maintain the resolver/API, documentation, validation, and release artifacts;
- convert MascotGO architecture decisions into route bindings;
- prepare the final V1 recommendation after comparative and real-query validation.

### Anthony — Qwen comparison

- run the existing Qwen classifier against the frozen blind benchmark;
- export predictions through the included V1 adapter;
- return route, confidence, latency, and validity fields without changing benchmark labels;
- do not tune against benchmark errors.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/1

### Tanvi — independent label-quality review

- review the 55-query manual adjudication queue against `ROUTING_LABEL_POLICY.md`;
- record one proposed route and a short rationale per query;
- flag genuinely context-dependent cases rather than forcing a label;
- do not edit the frozen benchmark.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2

### Edward — API and applicability test

- run the FastAPI or CLI smoke test;
- test at least 25 naturally phrased queries across all four route classes;
- include typos, shorthand, incomplete phrasing, and conversational requests;
- report expected route, actual route, confidence, and failure notes.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3

### Nimisha — product-scope and handoff review

- verify that the frozen objective still matches the intended project outcome;
- verify that the four route labels are sufficient;
- identify any missing product requirement before route bindings are finalized;
- keep product decisions synchronized across contributors.

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/4

### Ridhi and Anika

No blocking task is assigned while prior leave or availability constraints remain relevant. Either may contribute an independent test or label review when available.

## Decisions needed from Peter

1. **Invocation point:** Which MascotGO surfaces should call the resolver first: search bar, chat, GO button, or all three?
2. **Concrete route bindings:** What downstream service should each V1 label invoke today?
   - `short_circuit`
   - `medium`
   - `complex`
   - `llm_needed`
3. **Available request context:** Which optional fields can MascotGO reliably send, such as current page, active filters, known account role, prior query, or conversation history?
4. **Real-traffic validation:** Can the team receive a privacy-safe historical sample or shadow-mode query feed for validation beyond generated/curated data?
5. **Deployment boundary:** Should V1 run as a standalone FastAPI service, inside the existing application backend, or as a Microsoft Foundry callable action?

Tracking issue: https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5

## Non-negotiable evaluation guardrails

- Do not edit or relabel the frozen benchmark after observing model predictions.
- Do not let an exact normalized query appear in both training and benchmark data.
- Do not tune a model directly against frozen-benchmark errors.
- Do not claim mock, simulated, or adapted outputs as real model performance.
- Do not select a model on accuracy alone; false short-circuiting is release-critical.
- Do not permit a diagnostic model to become the recommended or packaged release model.
- Do not make persona, intent, or session context required until MascotGO confirms the integration contract.
- Any benchmark, label-policy, or route-semantics change creates a new version rather than silently rewriting V1 results.

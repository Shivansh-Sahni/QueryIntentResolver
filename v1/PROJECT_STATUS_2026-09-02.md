# Query Intent Resolver V1 — Project Status

**Updated:** September 2, 2026  
**Current technical coordinator:** Shivansh Sahni

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

The repository now contains an end-to-end reproducible system for:

- normalizing and auditing the six contributed datasets;
- resolving contradictory historical labels conservatively;
- quarantining unresolved labels instead of guessing;
- freezing a balanced, immutable held-out benchmark;
- preventing exact-query leakage between training and evaluation;
- training a calibrated query-only routing classifier;
- evaluating deterministic, learned, zero-shot, Qwen-adapter, and API-LLM tracks under one contract;
- measuring routing-specific safety, latency, and estimated cost;
- packaging the current release model behind Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces;
- validating hashes, runtime output, optional-context decoupling, and benchmark integrity in GitHub Actions.

The automated pipeline and generated artifacts are committed under `v1/`.

## Verified current evidence

### Data and benchmark

- Cleaned unique queries: **8,171**
- Unresolved unique queries quarantined for review: **55**
- Training rows after benchmark exclusion: **7,871**
- Frozen benchmark: **300 queries**
- Benchmark balance: **75 queries per route class**
- Exact normalized-query leakage: **0**
- Runtime contract validation: **passed**
- Release and benchmark hash validation: **passed**

### Current real query-only model

The current calibrated word/character/query-shape LinearSVC achieved:

- Accuracy: **78.0%**
- Macro F1: **0.7784**
- False short-circuit rate: **4.76%**
- Short-circuit recall: **53.33%**
- P95 local inference latency: **4.45 ms/query**
- Marginal local model API cost: **$0**

A diagnostic uncalibrated/raw model reached **84.0% accuracy**, but it produced a **15.28% false short-circuit rate**. It is not considered release-eligible because routing safety matters more than headline accuracy. The current selection process therefore rejects a model that is more accurate overall when it sends too many non-simple requests into the cheap path.

The reproducible zero-shot baseline was also completed on the identical benchmark and was not competitive with the supervised classifier.

## Current status

**Status: implementation complete; model selection remains provisional pending final comparative validation and MascotGO integration decisions.**

The codebase is ready for integration review. It is not yet a production-traffic guarantee because the current training and benchmark corpus is primarily generated/curated rather than sampled from live MascotGO traffic.

## Immediate parallel workstreams

### Shivansh — technical integration and final release

- preserve the V1 contract and frozen benchmark;
- coordinate and score every model export on the same benchmark;
- incorporate reviewed label decisions through the auditable merge script;
- maintain the resolver/API, documentation, and release artifacts;
- prepare the final recommendation after comparative and real-query validation.

### Anthony — Qwen comparison

- run the existing Qwen classifier against the frozen blind benchmark;
- export predictions through the included V1 adapter;
- return route, confidence, latency, and validity fields without changing benchmark labels;
- do not tune on benchmark errors.

### Tanvi — independent label-quality review

- review the 55-query manual adjudication queue against `ROUTING_LABEL_POLICY.md`;
- record one proposed route and a short rationale per query;
- flag genuinely context-dependent cases rather than forcing a label.

### Edward — API and applicability test

- run the FastAPI/CLI smoke test;
- test at least 25 naturally phrased queries across all four route classes;
- report incorrect routes, unclear outputs, and any failure to return the exact response contract.

### Nimisha — product-scope and handoff review

- verify that the frozen objective still matches the intended project outcome;
- review the current team handoff and identify any missing product requirement;
- help keep team decisions synchronized while the technical work is consolidated.

### Ridhi and Anika

- optional independent testing or label review when available; no blocking task is assigned while prior leave/availability constraints remain relevant.

## Decisions needed from Peter

1. **Invocation point:** Which MascotGO surfaces should call the resolver first: search bar, chat, GO button, or all three?
2. **Concrete route bindings:** What downstream service should each V1 label invoke today?
   - `short_circuit`
   - `medium`
   - `complex`
   - `llm_needed`
3. **Available request context:** Which optional fields can MascotGO reliably send, such as current page, active filters, known account role, prior query, or conversation history?
4. **Real-traffic validation:** Can the team receive a privacy-safe sample of historical or shadow-mode queries so V1 can be evaluated beyond generated/curated data before production use?
5. **Deployment boundary:** Should this run as a standalone FastAPI service, inside the existing application backend, or as a Microsoft Foundry callable action?

## Non-negotiable evaluation guardrails

- Do not edit or relabel the frozen benchmark after observing model predictions.
- Do not let an exact normalized query appear in both training and benchmark data.
- Do not claim mock, simulated, or adapted outputs as real model performance.
- Do not select a model on accuracy alone; false short-circuiting is a release-critical metric.
- Do not make persona, intent, or session context required until MascotGO confirms the integration contract.
- Any benchmark, label-policy, or route-semantics change creates a new version rather than silently rewriting V1 results.

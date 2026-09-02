# Query Intent Resolver

## V1: Implementation-ready routing classifier

The active implementation is under [`v1/`](./v1/). The complete repository map is in [`PROJECT_INDEX.md`](./PROJECT_INDEX.md).

V1 freezes the operational objective as:

> Given raw query text, predict the minimum handling complexity and routing tier required.

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

V1 includes:

- conservative cleanup of conflicting historical labels;
- a deterministic, balanced, query-disjoint frozen benchmark;
- a calibrated word/character/query-shape LinearSVC candidate;
- identical-benchmark runners for Anthony's Qwen classifier and optional language-model baselines;
- safety-first model selection emphasizing false short-circuit errors;
- reproducible reports, hashes, manifests, and validation;
- stable Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces;
- automated GitHub Actions build, testing, release packaging, artifact publication, and safe artifact commits.

### Current verified status

As of September 2, 2026:

- **11,575** raw contributed rows;
- **8,171** cleaned unique queries;
- **55** unresolved unique queries quarantined for review;
- **7,871** training queries after benchmark exclusion;
- **300-query** frozen benchmark, balanced at 75 examples per route;
- **0** exact normalized-query train/benchmark leakage;
- validated runtime contract, release hashes, benchmark hashes, optional-context decoupling, and Qwen blind-input integrity;
- latest automated GitHub Actions build: **passed**, including tests, model build, release packaging, artifact upload, and generated-artifact commit.

The current safety-focused supervised recommendation is provisional:

- Accuracy: **78.0%**
- Macro F1: **0.7784**
- False short-circuit rate: **4.76%**
- Short-circuit recall: **53.33%**
- P95 local inference latency: approximately **4.86 ms/query**
- Marginal local inference API cost: **$0**

A diagnostic variant reached **84.0% accuracy** and **0.8402 macro F1**, but its **15.28% false short-circuit rate** violates the routing-safety ceiling. Diagnostic models are now explicitly blocked from recommendation and packaging.

The recommendation remains provisional because the current real model does not yet meet the frozen minimum short-circuit recall, the Qwen comparison is pending, and the corpus has not yet been validated on privacy-safe real MascotGO traffic.

### Start here

1. [Complete project index](./PROJECT_INDEX.md)
2. [Current project status and ownership](./v1/PROJECT_STATUS_2026-09-02.md)
3. [Technical contract](./v1/CONTRACT.md)
4. [Implementation specification](./v1/IMPLEMENTATION_SPEC.md)
5. [Routing label policy](./v1/ROUTING_LABEL_POLICY.md)
6. [Team handoff](./v1/TEAM_HANDOFF.md)
7. [Generated validation report](./v1/artifacts/VALIDATION_REPORT.json)
8. [Model shootout](./v1/artifacts/shootout/SHOOTOUT_REPORT.md)
9. [Release manifest](./v1/artifacts/release/release_manifest.json)

The exact MascotGO or Microsoft Foundry attachment point remains configurable pending product-architecture confirmation. Optional context such as persona, current page, active filters, previous messages, and session data is deliberately decoupled from the V1 model.

## Historical work

The earlier repository work is retained for provenance:

1. **Part 1 - Phases 6 and 7**  
   Original complexity-first modeling experiments, contributor datasets, and the first label-ambiguity audit.

2. **Part 2 - Step 3**  
   Earlier standalone persona/intent validation package and reporting workflow.

The historical best strict grouped-query result was `0.816829`. V1 supersedes the earlier workflow by repairing contradictory labels, freezing one immutable benchmark, comparing candidates under one contract, prioritizing routing safety, and exposing a production-shaped resolver interface.

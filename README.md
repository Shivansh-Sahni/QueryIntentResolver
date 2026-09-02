# Query Intent Resolver

## V1: Implementation-ready routing classifier

The active V1 work is under [`v1/`](./v1/). It freezes the operational objective as:

> Given raw query text, predict the minimum handling complexity and routing tier required.

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

V1 includes:

- conservative cleanup of conflicting historical labels
- a deterministic, balanced, query-disjoint frozen benchmark
- calibrated word/character/query-shape LinearSVC baseline
- deterministic diagnostic baseline
- identical-benchmark adapters for Anthony's Qwen classifier and optional lightweight language-model baselines
- safety-weighted model selection emphasizing false short-circuit errors
- reproducible reports, hashes, manifests, and validation
- stable Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces
- automated GitHub Actions build and artifact publication

### Current verified status

As of September 2, 2026:

- 8,171 cleaned unique queries
- 55 unresolved unique queries quarantined for review
- 7,871 training queries after benchmark exclusion
- 300-query frozen benchmark, balanced at 75 examples per route
- zero exact-query train/benchmark leakage
- validated runtime contract, release hashes, and optional-context decoupling
- current safety-focused supervised model: 78.0% accuracy, 0.7784 macro F1, 4.76% false short-circuit rate, and approximately 4.45 ms P95 local inference latency

The model recommendation is provisional while the Qwen comparison, independent label review, and real-query shadow evaluation remain pending. A higher-accuracy diagnostic model was deliberately rejected because its false short-circuit rate was too high for safe routing.

Start here:

- [Current project status and ownership](./v1/PROJECT_STATUS_2026-09-02.md)
- [V1 README](./v1/README.md)
- [Technical contract](./v1/CONTRACT.md)
- [Implementation specification](./v1/IMPLEMENTATION_SPEC.md)
- [Routing label policy](./v1/ROUTING_LABEL_POLICY.md)
- [Team handoff](./v1/TEAM_HANDOFF.md)
- [Generated validation report](./v1/artifacts/VALIDATION_REPORT.json)
- [Model shootout](./v1/artifacts/shootout/SHOOTOUT_REPORT.md)

The exact MascotGO / Microsoft Foundry attachment point remains configurable pending product-architecture confirmation. Optional context such as persona, current page, active filters, previous messages, and session data is deliberately decoupled from the V1 model.

## Historical work

The earlier repository work is retained for provenance:

1. **Part 1 - Phases 6 and 7**  
   Original complexity-first modeling experiments and results.

2. **Part 2 - Step 3**  
   Earlier standalone persona/intent validation package.

The historical best strict grouped-query result was `0.816829`. V1 supersedes the earlier workflow by repairing contradictory labels, freezing one immutable benchmark, comparing every candidate on that benchmark, and exposing a production-shaped resolver contract.

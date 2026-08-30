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
- a deterministic, query-disjoint frozen benchmark
- calibrated word/character/query-shape LinearSVC baseline
- deterministic diagnostic baseline
- identical-benchmark adapters for Anthony's Qwen classifier and optional lightweight language-model baselines
- safety-weighted model selection emphasizing false short-circuit errors
- reproducible reports, hashes, manifests, and validation
- stable Python, CLI, FastAPI, Docker, and JSON Schema interfaces
- automated GitHub Actions build and artifact publication

Start here:

- [V1 README](./v1/README.md)
- [Technical contract](./v1/CONTRACT.md)
- [Implementation specification](./v1/IMPLEMENTATION_SPEC.md)
- [Routing label policy](./v1/ROUTING_LABEL_POLICY.md)
- [Team handoff](./v1/TEAM_HANDOFF.md)

The exact MascotGO / Microsoft Foundry attachment point remains configurable pending product-architecture confirmation. Optional context such as persona, current page, active filters, previous messages, and session data is deliberately decoupled from the V1 model.

## Historical work

The earlier repository work is retained for provenance:

1. **Part 1 - Phases 6 and 7**  
   Original complexity-first modeling experiments and results.

2. **Part 2 - Step 3**  
   Earlier standalone persona/intent validation package.

The historical best strict grouped-query result was `0.816829`. V1 supersedes the earlier workflow by repairing contradictory labels, freezing one immutable benchmark, comparing every candidate on that benchmark, and exposing a production-shaped resolver contract.

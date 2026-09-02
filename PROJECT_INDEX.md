# Query Intent Resolver — Complete Project Index

This is the navigation map for the full repository. It separates historical exploration from the active implementation so contributors can immediately identify the current source of truth.

## Start here

1. [`README.md`](./README.md) — concise overview and current verified headline metrics.
2. [`v1/PROJECT_STATUS_2026-09-02.md`](./v1/PROJECT_STATUS_2026-09-02.md) — complete current state, limitations, ownership, automation status, and MascotGO decisions required.
3. [`v1/CONTRACT.md`](./v1/CONTRACT.md) — frozen input/output contract.
4. [`v1/TEAM_HANDOFF.md`](./v1/TEAM_HANDOFF.md) — specific contributor responsibilities and execution instructions.
5. [`v1/artifacts/VALIDATION_REPORT.json`](./v1/artifacts/VALIDATION_REPORT.json) — machine-readable validation result.
6. [`v1/artifacts/shootout/SHOOTOUT_REPORT.md`](./v1/artifacts/shootout/SHOOTOUT_REPORT.md) — current identical-benchmark model comparison and recommendation.
7. [`v1/artifacts/release/release_manifest.json`](./v1/artifacts/release/release_manifest.json) — packaged release identity, hashes, model metrics, and integration status.

## Active implementation: `v1/`

The active system predicts the minimum routing tier required from raw query text:

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

### Product and technical specifications

- [`v1/CONTRACT.md`](./v1/CONTRACT.md) — required input, output, and future-compatible optional fields.
- [`v1/IMPLEMENTATION_SPEC.md`](./v1/IMPLEMENTATION_SPEC.md) — system architecture and implementation details.
- [`v1/ROUTING_LABEL_POLICY.md`](./v1/ROUTING_LABEL_POLICY.md) — canonical route definitions and adjudication policy.
- [`v1/PROJECT_STATUS_2026-09-02.md`](./v1/PROJECT_STATUS_2026-09-02.md) — verified current status and exact remaining gates.
- [`v1/TEAM_HANDOFF.md`](./v1/TEAM_HANDOFF.md) — contributor assignments and guardrails.
- [`v1/CHANGELOG.md`](./v1/CHANGELOG.md) — version history.

### Implementation directories

- `v1/config/` — frozen routing and winner-selection policy.
- `v1/data/` — manual overrides and review inputs.
- `v1/scripts/` — cleanup, benchmark, modeling, comparison, release, and validation commands.
- `v1/src/qir_v1/` — resolver library, API, features, evaluation, policy, schemas, and CLI.
- `v1/tests/` — automated contract and pipeline tests.
- `v1/schemas/` — machine-readable request and response definitions.
- `v1/docs/` — integration, review, and operational documentation.
- `v1/notebooks/` — optional interactive workflows.
- `v1/artifacts/` — generated datasets, benchmark, model results, release bundle, and validation records.

### Generated artifact map

- `v1/artifacts/data_cleanup/` — normalized data, conflict audit, invalid-label audit, and manual-review queue.
- `v1/artifacts/benchmark/` — immutable gold benchmark, blind model inputs, training split, hashes, and leakage checks.
- `v1/artifacts/models/` — predictions, metrics, and placeholders for each model track.
- `v1/artifacts/shootout/` — safety-first model leaderboard and recommendation.
- `v1/artifacts/release/` — packaged runtime model, release manifest, model card, and sample outputs.
- `v1/artifacts/VALIDATION_REPORT.json` — final integrity, model-eligibility, and runtime checks.
- `v1/artifacts/BUILD_STATUS.json` — latest automated build provenance.

### Reproduce the active system

```bash
python -m pip install -r v1/requirements.txt
python v1/scripts/run_v1_pipeline.py --benchmark-size 300
```

Run the service:

```bash
PYTHONPATH=v1/src uvicorn qir_v1.api:app --host 0.0.0.0 --port 8000
```

### Continuous integration

The active workflow is `.github/workflows/qir-v1-pipeline.yml`. It runs core tests, data cleanup, immutable benchmark validation, model training, safety-first comparison, release packaging, artifact validation, artifact upload, and generated-artifact publication. The latest full run passed.

The obsolete one-time bootstrap workflow has been removed.

## Historical work retained for provenance

Historical directories document how the project evolved. They are not the current implementation source of truth.

### `Part 1 - Phases 6 and 7/`

Contains:

- the six contributed raw CSV sources;
- the original complexity-first model sweep;
- the earlier grouped-query evaluation;
- the original `0.816829` strict grouped-query result;
- the first label-ambiguity audit.

Use this section for methodological history and data provenance. Use `v1/` for current development.

### `Part 2 - Step 3/`

Contains the earlier standalone persona/intent validation package, including:

- benchmark creation;
- prediction-export contracts;
- persona and intent scoring;
- route derivation;
- report generation;
- mock demonstration outputs.

Mock outputs in this historical package are illustrative only and are not current model evidence.

## Current GitHub work items

- [Issue #1 — Qwen comparison on the frozen benchmark](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/1)
- [Issue #2 — independent manual-label adjudication](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2)
- [Issue #3 — API and natural-query applicability testing](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3)
- [Issue #4 — V1 product-scope confirmation](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/4)
- [Issue #5 — MascotGO route binding and deployment decisions](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5)

## Source-of-truth rules

- The V1 objective, labels, and response contract come from `v1/CONTRACT.md` and `v1/ROUTING_LABEL_POLICY.md`.
- The current project statement and responsibility map come from `v1/PROJECT_STATUS_2026-09-02.md` and `v1/TEAM_HANDOFF.md`.
- The frozen benchmark must not be edited after predictions are observed.
- Model claims must come from committed `metrics.json`, the shootout report, release manifest, or validation report.
- Diagnostic models can be analyzed but cannot be recommended or packaged.
- Mock or simulated predictions must never be presented as real performance.
- Product integration assumptions remain configurable until MascotGO confirms downstream route bindings and available request context.
- A material change to route semantics, label policy, or the benchmark must create a new version rather than silently replacing V1 evidence.

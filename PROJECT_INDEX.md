# Query Intent Resolver — Complete Project Index

This is the navigation map for the full repository. It separates historical exploration, archived experiments, and the active implementation so contributors can immediately identify the current source of truth.

## Start here

1. [`v1/CURRENT_STATUS.md`](./v1/CURRENT_STATUS.md) — live project state, results, ownership, completed work, and remaining gates.
2. [`README.md`](./README.md) — concise overview and verified headline metrics.
3. [`v1/CONTRACT.md`](./v1/CONTRACT.md) — frozen input/output contract.
4. [`v1/TEAM_HANDOFF.md`](./v1/TEAM_HANDOFF.md) — active contributor responsibilities and execution instructions.
5. [`v1/artifacts/VALIDATION_REPORT.json`](./v1/artifacts/VALIDATION_REPORT.json) — machine-readable validation result.
6. [`v1/artifacts/shootout/SHOOTOUT_REPORT.md`](./v1/artifacts/shootout/SHOOTOUT_REPORT.md) — current identical-benchmark model comparison and recommendation.
7. [`v1/artifacts/release/release_manifest.json`](./v1/artifacts/release/release_manifest.json) — packaged release identity, hashes, model metrics, and integration status.

The earlier dated status file, [`v1/PROJECT_STATUS_2026-09-02.md`](./v1/PROJECT_STATUS_2026-09-02.md), is retained as a historical checkpoint.

## Active implementation: `v1/`

The active system predicts the minimum routing tier required from raw query text:

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

### Product and technical specifications

- [`v1/CURRENT_STATUS.md`](./v1/CURRENT_STATUS.md) — current evidence and ownership.
- [`v1/CONTRACT.md`](./v1/CONTRACT.md) — required input, output, and future-compatible optional fields.
- [`v1/IMPLEMENTATION_SPEC.md`](./v1/IMPLEMENTATION_SPEC.md) — system architecture and implementation details.
- [`v1/ROUTING_LABEL_POLICY.md`](./v1/ROUTING_LABEL_POLICY.md) — canonical route definitions and adjudication policy.
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
- `v1/artifacts/models/linearsvc/` — recommended supervised candidate and diagnostic variant.
- `v1/artifacts/models/qwen/` — Anthony's preserved raw export, scored predictions, metrics, errors, and report.
- `v1/artifacts/models/rules/` — deterministic diagnostic baseline.
- `v1/artifacts/models/zero_shot/` and `llm/` — optional model tracks.
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

The active workflow is `.github/workflows/qir-v1-pipeline.yml`. It runs core tests, data cleanup, immutable benchmark validation, model training, external Qwen-export preservation and scoring, safety-first comparison, release packaging, artifact validation, artifact upload, and generated-artifact publication. The latest full run passed.

## Archived experimental modeling

### `research_archive/2026-08-30-hardcore-v1/`

This directory preserves a parallel local hybrid-router experiment that used a smaller 4,620-row subset and a separate 552-query benchmark. It reported a 91.30% Logistic Regression result and a 93.30% hybrid rule-plus-Logistic Regression result, but also only 50% accuracy on a small out-of-distribution stress suite.

The archive explains why these results are not directly comparable to, and do not replace, the canonical V1.0.1 metrics. Its useful ideas include template-family leakage checks, under/over-routing metrics, confidence-versus-coverage analysis, and high-precision deterministic gates.

- [Archived experiment report and interpretation rules](./research_archive/2026-08-30-hardcore-v1/README.md)

## Historical work retained for provenance

### `Part 1 - Phases 6 and 7/`

Contains the six contributed raw CSV sources, original complexity-first model sweep, earlier grouped-query evaluation, historical `0.816829` result, and first label-ambiguity audit.

### `Part 2 - Step 3/`

Contains the earlier standalone persona/intent validation package, prediction-export contracts, scoring, route derivation, reporting, and mock demonstration outputs. Mock outputs are illustrative only and are not current model evidence.

## GitHub work items

Open:

- [Issue #2 — unresolved-label adjudication](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/2)
- [Issue #3 — API and natural-query applicability testing](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/3)
- [Issue #5 — MascotGO route binding and deployment decisions](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/5)

Completed:

- [Issue #1 — Qwen comparison on the frozen benchmark](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/1)
- [Issue #4 — V1 product-scope confirmation](https://github.com/Shivansh-Sahni/QueryIntentResolver/issues/4)

## Source-of-truth rules

- The V1 objective, labels, and response contract come from `v1/CONTRACT.md` and `v1/ROUTING_LABEL_POLICY.md`.
- The current project statement and responsibility map come from `v1/CURRENT_STATUS.md` and `v1/TEAM_HANDOFF.md`.
- The frozen benchmark must not be edited after predictions are observed.
- Model claims must come from committed `metrics.json`, the shootout report, release manifest, or validation report.
- Diagnostic models can be analyzed but cannot be recommended or packaged.
- Archived experimental metrics must remain explicitly separated from current release metrics.
- Mock or simulated predictions must never be presented as real performance.
- Product integration assumptions remain configurable until MascotGO confirms downstream route bindings and available request context.
- A material change to route semantics, label policy, or the benchmark must create a new version rather than silently replacing V1 evidence.

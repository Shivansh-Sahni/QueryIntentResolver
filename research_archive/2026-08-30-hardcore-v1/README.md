# Archived Experimental Modeling Pass — August 30, 2026

## Status

**Archived research experiment. Not the canonical V1 release.**

The current source of truth remains:

- [`/v1/CONTRACT.md`](../../v1/CONTRACT.md)
- [`/v1/PROJECT_STATUS_2026-09-02.md`](../../v1/PROJECT_STATUS_2026-09-02.md)
- [`/v1/artifacts/`](../../v1/artifacts)

This archive preserves a parallel local modeling pass so its useful ideas and reported results are not lost or confused with the active release.

## Experimental objective

Given raw query text, predict one of:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

The public output contract remained `{route, confidence}`.

## Dataset and cleanup used in this pass

This experiment used a smaller 4,620-row consolidated subset rather than the full canonical repository corpus.

- Raw rows: **4,620**
- Normalized unique queries: **2,699**
- Conflicting unique queries: **209**
- Resolved unique queries: **2,627**
- Quarantined for manual review: **72**

Conflict handling was query-level:

1. normalize exact query strings;
2. use historical intent metadata only as annotation evidence;
3. accept an unambiguous intent-to-route mapping where available;
4. otherwise accept a strong observed majority only at at least 67% with a margin of at least two rows;
5. quarantine unresolved queries rather than guessing.

## Separate experimental benchmark

This pass created a separate benchmark that must not be confused with the canonical 300-query V1 benchmark.

- Benchmark version: `QIR-V1.0` within the local experiment
- Seed: `20260830`
- Benchmark rows: **552**
- Training rows after family exclusion: **1,435**
- Exact normalized-query overlap: **0**
- Generalized template-family overlap: **0**
- Benchmark SHA-256: `5cb70a65d0fcaf21a35bb6f8f8a8e86710ef3dd8aac536022832e1fc12bbb0ec`

Benchmark distribution:

| Route | Rows |
| --- | ---: |
| `complex` | 246 |
| `medium` | 152 |
| `short_circuit` | 104 |
| `llm_needed` | 50 |

Training distribution:

| Route | Rows |
| --- | ---: |
| `complex` | 774 |
| `medium` | 417 |
| `short_circuit` | 209 |
| `llm_needed` | 35 |

## Models tested

The local model sweep compared:

- multinomial Logistic Regression;
- LinearSVC with multiple regularization values;
- SGD log-loss;
- Complement Naive Bayes;
- a hybrid deterministic-rule layer with Logistic Regression fallback.

All learned models used query text only.

## Experimental results

### Best pure learned model: Logistic Regression

- Accuracy: **91.30%**
- Macro F1: **0.8876**
- Weighted F1: **0.9129**
- Balanced accuracy: **0.8832**
- MCC: **0.8726**
- False short-circuit rate: **2.68%**
- Short-circuit false-discovery rate: **11.54%**
- Under-route rate: **4.89%**
- Over-route rate: **3.80%**
- Mean measured local latency: approximately **0.91 ms/query**
- P95 measured local latency: approximately **1.35 ms/query**
- Marginal model API cost: **$0**

### Experimental hybrid: deterministic rules + Logistic Regression

- Accuracy: **93.30%**
- Macro F1: **0.9354**
- Balanced accuracy: **0.9226**
- MCC: **0.9018**
- False short-circuit rate: **0.89%**
- Short-circuit false-discovery rate: **4.12%**
- Under-route rate: **1.45%**
- Over-route rate: **5.25%**
- Deterministic-rule coverage: **43.66%**
- Mean measured local latency: approximately **1.22 ms/query**
- P95 measured local latency: approximately **3.41 ms/query**
- Marginal model API cost: **$0**

### Out-of-distribution warning

A small hand-authored 12-query stress suite achieved only **50% accuracy**. This is a major limitation and is one reason the experimental hybrid was not promoted directly into the canonical release.

## Useful contributions from this experiment

The experiment introduced several ideas worth testing in a future versioned release:

- generalized template-family leakage checks;
- explicit under-route and over-route metrics;
- short-circuit false-discovery rate;
- high-precision deterministic gates before a learned fallback;
- confidence-versus-coverage tables;
- empirical stress testing distinct from the frozen benchmark;
- native probability output through Logistic Regression.

## Why these headline metrics are not the current release metrics

The 93.30% hybrid result and 91.30% Logistic Regression result are not directly comparable to the canonical V1.0.1 numbers because this experiment used:

1. a smaller data subset;
2. a different benchmark size and class distribution;
3. a different train/benchmark family exclusion process;
4. a hand-authored deterministic rule layer;
5. a largely synthetic and curated corpus;
6. no integration into the canonical GitHub Actions release pipeline;
7. a stress suite that showed substantial real-world generalization weakness.

For those reasons, these results are preserved as **experimental evidence**, not substituted for the active release recommendation.

## Promotion path

A future V1.1 experiment may port the promising hybrid and family-split ideas into the canonical pipeline. Promotion requires:

- a versioned benchmark decision made before observing new results;
- complete reproducible training code;
- identical evaluation of every candidate;
- preservation of false-short-circuit safety checks;
- a substantially larger real-query applicability set;
- comparison against the current canonical candidate;
- no silent replacement of V1.0.1 evidence.

## Interpretation rule

Use this archive for research history and candidate ideas. Use `/v1/artifacts/`, the current shootout, release manifest, and validation report for current implementation claims.

# Query Intent Resolver V1 Implementation Specification

## System boundary

V1 answers one operational question:

> What handling route does this query require?

It does not generate the final answer, manage search state, infer a persistent user persona, or orchestrate downstream agents. It returns a route and confidence to the caller.

## Route definitions

| Route | Handling requirement | Typical examples |
| --- | --- | --- |
| `short_circuit` | Deterministic entity or indexed one-hop lookup | `MIT`, `UCLA tuition` |
| `medium` | Ordinary factual retrieval, process lookup, or one-to-two-filter search | `colleges in California`, `Stanford deadline` |
| `complex` | Comparison, recommendation, ranking, multi-constraint search, planning, or multi-step workflow | `UCLA vs USC for engineering`, `affordable CS schools near the beach with good outcomes` |
| `llm_needed` | Subjective, ambiguous, advisory, emotional, or rewrite-heavy interpretation | `schools with normal people`, `what college would feel right for me` |

## Data cleanup

The raw six-file dataset contains repeated exact queries and contradictory labels. The cleanup pipeline:

1. normalizes Unicode, case, whitespace, punctuation, labels, and column names;
2. groups all identical normalized queries;
3. applies explicit manual overrides for high-volume known conflicts;
4. accepts unanimous observed labels;
5. uses the frozen intent-to-route policy when recognized intents agree;
6. accepts only strong route or intent majorities;
7. sends remaining cases to a manual-review queue;
8. retains one training row per normalized query.

The output preserves full provenance through source file names and row numbers.

## Benchmark freeze

The benchmark is deterministically sampled with seed `20260830` from high-confidence cleaned examples. It is:

- disjoint from the training pool by normalized query;
- stratified across all four routes;
- assigned stable benchmark IDs;
- protected by SHA-256 hashes in a manifest;
- never used to tune labels, thresholds, prompts, or features after freeze.

## Models

### LinearSVC baseline

- word TF-IDF, 1-2 grams;
- character TF-IDF, 3-5 grams;
- small deterministic query-shape feature block;
- class-balanced LinearSVC;
- sigmoid calibration for confidence scores.

### Anthony Qwen adapter

Anthony's Qwen model predicts persona and intent rather than route directly. The adapter maps predicted intent to the frozen V1 route taxonomy. A GPU script and benchmark export adapter are included. This model must be scored on the exact frozen benchmark before it can be selected.

### Lightweight language-model baseline

Two paths are supported:

- a local zero-shot NLI language model with no provider key;
- a configurable OpenAI-compatible chat-completions endpoint for a paid lightweight LLM.

Both produce the same prediction-export schema and are evaluated identically.

## Evaluation

Every completed model is measured on:

- accuracy;
- macro F1;
- false short-circuit rate;
- short-circuit recall;
- median and P95 latency;
- estimated cost per 1,000 queries;
- per-route precision, recall, and F1;
- confusion matrix and row-level errors.

False short-circuit rate is defined as the fraction of queries predicted `short_circuit` that should have been routed elsewhere. This is the primary dangerous-routing metric.

## Winner selection

A model must have full benchmark coverage and satisfy minimum safety and quality guardrails. Ranking then prioritizes:

1. macro F1;
2. accuracy;
3. false short-circuit safety;
4. short-circuit recall;
5. latency and cost.

A winner remains provisional until at least two real models have been evaluated on the identical frozen benchmark.

## Runtime

The provisional winner is copied into `v1/artifacts/release/model.joblib` and exposed through a stable Python class and FastAPI endpoint. Optional context remains decoupled.

# Query Intent Resolver V1 Model Shootout

- Status: **provisional**
- Recommended model: **calibrated_word_char_shape_linearsvc**
- Selection basis: **best_real_model_passing_quality_and_false_short_circuit_guardrails**
- Highest raw score (analysis only): **calibrated_word_char_shape_linearsvc_raw**
- Verified real models: **1**
- Benchmark SHA-256: `591a31c4947d73fa7d77d2a94f32a69e689281c48a564d08317865b826bd84c6`
- Why provisional: No real model currently passes every release guardrail, including minimum short-circuit recall.

| Rank | Model | Tier | Status | Verified | Eligible | Safety candidate | Accuracy | Macro F1 | False SC | SC Recall | P95 ms | Cost / 1K |
| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `calibrated_word_char_shape_linearsvc` | provisional_safe | real | True | False | True | 0.7800 | 0.7784 | 0.0476 | 0.5333 | 4.862 | $0.000000 |
| 2 | `calibrated_word_char_shape_linearsvc_raw` | diagnostic_only | diagnostic | True | False | False | 0.8400 | 0.8402 | 0.1528 | 0.8133 | 4.862 | $0.000000 |
| 3 | `deterministic_rules_v1` | diagnostic_only | diagnostic | True | False | False | 0.4333 | 0.3930 | 0.6364 | 0.1600 | 0.010 | $0.000000 |

## Decision order

1. Require a real model, the identical frozen benchmark, and complete coverage.
2. Prefer models passing all release guardrails.
3. If none pass all guardrails, recommend the best real model that still passes the false-short-circuit safety ceiling and core quality floors.
4. Rank within a selection tier by the frozen safety-weighted score.
5. Use latency and cost as tie-breakers among comparable models.

Diagnostic entries remain visible for transparency but cannot be recommended or packaged.

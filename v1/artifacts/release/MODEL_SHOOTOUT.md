# Query Intent Resolver V1 Model Shootout

- Status: **provisional**
- Current leader: **calibrated_word_char_shape_linearsvc_raw**
- Verified real models: **2**
- Benchmark SHA-256: `591a31c4947d73fa7d77d2a94f32a69e689281c48a564d08317865b826bd84c6`

| Rank | Model | Status | Benchmark Verified | Eligible | Accuracy | Macro F1 | False SC | SC Recall | P95 ms | Cost / 1K |
| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `calibrated_word_char_shape_linearsvc_raw` | diagnostic | True | False | 0.8400 | 0.8402 | 0.1528 | 0.8133 | 4.445 | $0.000000 |
| 2 | `calibrated_word_char_shape_linearsvc` | real | True | False | 0.7800 | 0.7784 | 0.0476 | 0.5333 | 4.445 | $0.000000 |
| 3 | `deterministic_rules_v1` | diagnostic | True | False | 0.4333 | 0.3930 | 0.6364 | 0.1600 | 0.010 | $0.000000 |
| 4 | `zero_shot::typeform/distilbert-base-uncased-mnli` | real | True | False | 0.2433 | 0.1800 | 0.0000 | 0.0000 | 107.276 | $0.001712 |

## Decision order

1. Identical frozen benchmark and complete coverage.
2. Pass false-short-circuit and quality guardrails.
3. Rank by the frozen safety-weighted score.
4. Use latency and cost as tie-breakers among comparable models.

Diagnostic entries are reported for transparency but cannot win.

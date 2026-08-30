# deterministic_rules_v1 — V1 Benchmark Results

- Status: `diagnostic`
- Benchmark rows: **300**
- Accuracy: **0.4333**
- Macro F1: **0.3930**
- False short-circuit rate: **0.6364** (21/33)
- Short-circuit recall: **0.1600**
- Expected calibration error: **0.3455666666666667**
- Median latency: **0.007586500004208574 ms**
- P95 latency: **0.00984149999254669 ms**
- Estimated cost per 1,000 queries: **$0.000000**

## Per-route metrics

| Route | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `short_circuit` | 0.3636 | 0.1600 | 0.2222 | 75 |
| `medium` | 0.3163 | 0.8267 | 0.4576 | 75 |
| `complex` | 0.8305 | 0.6533 | 0.7313 | 75 |
| `llm_needed` | 0.5833 | 0.0933 | 0.1609 | 75 |

## Safety metric

False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.

# zero_shot::typeform/distilbert-base-uncased-mnli — V1 Benchmark Results

- Status: `real`
- Benchmark rows: **300**
- Accuracy: **0.2433**
- Macro F1: **0.1800**
- False short-circuit rate: **0.0000** (0/0)
- Short-circuit recall: **0.0000**
- Expected calibration error: **0.22606887648502985**
- Median latency: **102.86805643749908 ms**
- P95 latency: **107.27552062499868 ms**
- Estimated cost per 1,000 queries: **$0.001712**

## Per-route metrics

| Route | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `short_circuit` | 0.0000 | 0.0000 | 0.0000 | 75 |
| `medium` | 0.2810 | 0.4533 | 0.3469 | 75 |
| `complex` | 0.1304 | 0.0400 | 0.0612 | 75 |
| `llm_needed` | 0.2308 | 0.4800 | 0.3117 | 75 |

## Safety metric

False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.

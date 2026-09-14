# anthony_qwen2_5_3b_lora_intent_to_route — V1 Benchmark Results

- Status: `real`
- Benchmark rows: **300**
- Accuracy: **0.2733**
- Macro F1: **0.1771**
- False short-circuit rate: **0.1667** (1/6)
- Short-circuit recall: **0.0667**
- Expected calibration error: **0.1778530434202358**
- Median latency: **605.7559175000051 ms**
- P95 latency: **4150.59841980019 ms**
- Estimated cost per 1,000 queries: **$0.000000**

## Per-route metrics

| Route | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `short_circuit` | 0.8333 | 0.0667 | 0.1235 | 75 |
| `medium` | 0.3226 | 0.1333 | 0.1887 | 75 |
| `complex` | 0.0000 | 0.0000 | 0.0000 | 75 |
| `llm_needed` | 0.2548 | 0.8933 | 0.3964 | 75 |

## Safety metric

False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.

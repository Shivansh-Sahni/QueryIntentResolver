# calibrated_word_char_shape_linearsvc — V1 Benchmark Results

- Status: `real`
- Benchmark rows: **300**
- Accuracy: **0.7800**
- Macro F1: **0.7784**
- False short-circuit rate: **0.0476** (2/42)
- Short-circuit recall: **0.5333**
- Expected calibration error: **0.08599622104840003**
- Median latency: **4.001338500003726 ms**
- P95 latency: **4.4449871000040275 ms**
- Estimated cost per 1,000 queries: **$0.000000**

## Per-route metrics

| Route | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `short_circuit` | 0.9524 | 0.5333 | 0.6838 | 75 |
| `medium` | 0.6139 | 0.8267 | 0.7045 | 75 |
| `complex` | 0.9437 | 0.8933 | 0.9178 | 75 |
| `llm_needed` | 0.7558 | 0.8667 | 0.8075 | 75 |

## Safety metric

False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.

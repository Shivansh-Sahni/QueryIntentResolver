# calibrated_word_char_shape_linearsvc_raw — V1 Benchmark Results

- Status: `diagnostic`
- Benchmark rows: **300**
- Accuracy: **0.8400**
- Macro F1: **0.8402**
- False short-circuit rate: **0.1528** (11/72)
- Short-circuit recall: **0.8133**
- Expected calibration error: **0.07255846524312053**
- Median latency: **4.001338500003726 ms**
- P95 latency: **4.4449871000040275 ms**
- Estimated cost per 1,000 queries: **$0.000000**

## Per-route metrics

| Route | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `short_circuit` | 0.8472 | 0.8133 | 0.8299 | 75 |
| `medium` | 0.7763 | 0.7867 | 0.7815 | 75 |
| `complex` | 0.9189 | 0.9067 | 0.9128 | 75 |
| `llm_needed` | 0.8205 | 0.8533 | 0.8366 | 75 |

## Safety metric

False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.

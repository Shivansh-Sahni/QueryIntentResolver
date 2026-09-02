# Query Intent Resolver V1 - LinearSVC Model Card

## Purpose

Predict one of four handling routes from raw query text:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

## Training

- Training rows: **7871** unique normalized queries
- Held-out benchmark rows: **300**
- Benchmark leakage check: **passed**
- Features: word TF-IDF, character TF-IDF, deterministic query-shape features
- Classifier: calibrated LinearSVC
- Training time: **1.701 seconds**

## Deployment-policy benchmark results

- Accuracy: **0.7800**
- Macro F1: **0.7784**
- False short-circuit rate: **0.0476**
- Short-circuit recall: **0.5333**
- P95 single-query latency: **4.862 ms**
- API cost: **$0.00 per query**

## Raw-model diagnostic results

- Accuracy: **0.8400**
- Macro F1: **0.8402**
- False short-circuit rate: **0.1528**

## Known limitations

The source data is predominantly synthetic and previously contained conflicting exact-query labels. V1 removes unresolved conflicts and freezes a disjoint benchmark, but production validation must eventually include naturally occurring MascotGO queries.

## Runtime contract

```json
{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}
```

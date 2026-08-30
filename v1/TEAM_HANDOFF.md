# Query Intent Resolver V1 Team Handoff

## What is frozen

- Goal: route complexity, not persona prediction.
- Required model input: raw query text only.
- Required output: route plus confidence.
- Route labels: `short_circuit`, `medium`, `complex`, `llm_needed`.
- Benchmark seed: `20260830`.
- Final MascotGO and Foundry binding: configurable pending architecture confirmation.

## What runs now

```bash
python v1/scripts/run_v1_pipeline.py
```

This performs label cleanup, benchmark freeze, LinearSVC training, evaluation, provisional model selection, release packaging, sample inference, and integrity checks.

## Files to review first

1. `v1/artifacts/data_cleanup/cleanup_summary.json`
2. `v1/artifacts/data_cleanup/manual_review_queue.csv`
3. `v1/artifacts/benchmark/benchmark_manifest.json`
4. `v1/artifacts/models/linearsvc/REPORT.md`
5. `v1/artifacts/shootout/SHOOTOUT_REPORT.md`
6. `v1/artifacts/release/release_manifest.json`

## Team actions

### Shivansh

- maintain the V1 contract;
- run the integrated pipeline;
- review unresolved labels;
- compare model exports;
- maintain the release and engineering handoff.

### Anthony

- run `v1/scripts/run_qwen_benchmark.py` on a GPU using the frozen benchmark;
- return the generated prediction CSV without changing benchmark labels;
- do not retrain or tune against benchmark errors.

### Other team members

- independently review the manual-label queue using the frozen policy;
- test API outputs and collect naturally occurring query examples;
- do not edit the frozen benchmark.

## Qwen scoring commands

```bash
python v1/scripts/run_qwen_benchmark.py \
  --benchmark v1/artifacts/benchmark/benchmark_gold.csv \
  --output v1/artifacts/models/qwen/predictions.csv

python v1/scripts/score_prediction_export.py \
  --benchmark v1/artifacts/benchmark/benchmark_gold.csv \
  --predictions v1/artifacts/models/qwen/predictions.csv \
  --output-dir v1/artifacts/models/qwen \
  --model-name anthony_qwen2_5_3b_lora_intent_to_route
```

## LLM baseline commands

```bash
python v1/scripts/run_llm_baseline.py \
  --benchmark v1/artifacts/benchmark/benchmark_gold.csv \
  --output v1/artifacts/models/llm/predictions.csv \
  --endpoint "$QIR_LLM_ENDPOINT" \
  --api-key "$QIR_LLM_API_KEY" \
  --model "$QIR_LLM_MODEL"
```

Then score the export with `score_prediction_export.py`.

## API

```bash
PYTHONPATH=v1/src uvicorn qir_v1.api:app --host 0.0.0.0 --port 8000
```

Request:

```bash
curl -X POST http://localhost:8000/v1/resolve \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"UCLA vs USC for engineering"}'
```

Response:

```json
{
  "route": "complex",
  "confidence": 0.91
}
```

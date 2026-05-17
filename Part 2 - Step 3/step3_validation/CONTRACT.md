# Step 3 Validation Contract

This package assumes two external inputs:

1. A cleaned labeled dataset from step 1
2. A prediction export from step 2

It does not assume any specific model runtime or serving stack.

## Benchmark Input Contract

Required columns:

- `Query`
- `Persona`
- `Intent`

Optional:

- `Entities`

The benchmark builder produces:

- `benchmark_gold.csv`
- `benchmark_review_template.csv`
- `benchmark_exclusion_manifest.csv`
- `benchmark_summary.json`

Benchmark integrity rules:

- exact duplicate queries with the same persona and intent are collapsed to one benchmark candidate
- exact duplicate queries with conflicting persona or intent labels are excluded from the benchmark pool

## Prediction Export Contract

Required:

- `row_id` or exact `query`
- `predicted_persona`
- `predicted_intent`
- `predicted_confidence`

Optional but expected for final reporting:

- `predicted_entities_json`
- `model`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`

## Derived Routing Contract

The evaluator derives:

- `predicted_route_tier`
- `predicted_short_circuit`
- `gold_route_tier`
- `gold_short_circuit`

Route tiers are derived from `Intent` using
`config/intent_to_route_tier.json`.

## Output Contract

The evaluator writes:

- `evaluation_summary.json`
- `evaluation_report.md`
- `evaluation_dashboard.html`
- `prediction_errors.csv`
- `matched_predictions_enriched.csv`
- `confidence_band_summary.csv`
- `persona_accuracy_by_slice.csv`
- `intent_accuracy_by_slice.csv`
- `top_persona_confusions.csv`
- `top_intent_confusions.csv`
- `persona_confusion_matrix.csv`
- `intent_confusion_matrix.csv`
- `route_tier_confusion_matrix.csv`

## Integrity Rules

- benchmark rows are joined to predictions by `row_id` first, then exact query
- query-based fallback is rejected if either side has duplicate query strings
- labels and predictions must each have unique join keys
- benchmark gold intents must exist in the checked-in route mapping
- route tier is never trusted from the prediction export; it is always derived
- confidence below `0.40` forces predicted route tier to `fallback`
- unknown predicted intents are forced to `fallback` and reported separately
- entities are logged only and not scored in v1

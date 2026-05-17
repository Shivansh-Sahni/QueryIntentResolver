# Step 3 Validation Package

This package implements the current step-3 workflow only. It does not depend on
older project code or older phase outputs.

## What it does

- creates a fixed held-out benchmark from a cleaned dataset
- defines the prediction export contract for step 2
- evaluates persona, intent, joint accuracy, derived route tier, and short-circuit behavior
- emits machine-readable and human-readable reports
- includes a mock prediction generator so you can show a successful dry run now
- guards against ambiguous query-based joins and conflicting duplicate benchmark queries

## Package layout

- `scripts/create_validation_benchmark.py`
- `scripts/mock_prediction_export.py`
- `scripts/evaluate_classifier.py`
- `scripts/run_demo_pipeline.py`
- `config/intent_to_route_tier.json`
- `templates/predictions_template.csv`
- `fixtures/sample_clean_dataset.csv`
- `CONTRACT.md`
- `tests/run_smoke_test.py`

## Required input dataset

The benchmark builder expects a cleaned CSV from step 1 with these columns:

- `Query`
- `Persona`
- `Intent`

Optional:

- `Entities`

The benchmark builder also applies two integrity checks before sampling:

- drops exact duplicate queries when they carry the same persona and intent
- excludes exact duplicate queries when they carry conflicting persona or intent labels

## Prediction contract

The evaluator expects prediction exports with these columns:

- `row_id` or `query`
- `predicted_persona`
- `predicted_intent`
- `predicted_confidence`
- `predicted_entities_json`
- `model`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`

## Route derivation

The evaluator derives route tier from intent using
`config/intent_to_route_tier.json`.

Route tiers:

- `short_circuit`
- `standard_search`
- `agentic`
- `fallback`

`fallback` is also forced when `predicted_confidence < 0.40`.

## Commands

Create a benchmark:

```bash
python3 step3_validation/scripts/create_validation_benchmark.py \
  --source path/to/cleaned_dataset.csv \
  --output-dir step3_validation/reports/benchmark_run \
  --benchmark-size 200
```

Generate a mock prediction export:

```bash
python3 step3_validation/scripts/mock_prediction_export.py \
  --labels step3_validation/reports/benchmark_run/benchmark_gold.csv \
  --output step3_validation/reports/benchmark_run/mock_predictions.csv
```

Run evaluation:

```bash
python3 step3_validation/scripts/evaluate_classifier.py \
  --labels step3_validation/reports/benchmark_run/benchmark_gold.csv \
  --predictions step3_validation/reports/benchmark_run/mock_predictions.csv \
  --output-dir step3_validation/reports/benchmark_run/evaluation
```

Run the smoke test:

```bash
python3 step3_validation/tests/run_smoke_test.py
```

Run the full illustrative demo pipeline:

```bash
python3 step3_validation/scripts/run_demo_pipeline.py --clean
```

## Evaluation outputs

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

## Current sample outputs

The package is designed to support two modes:

- real validation later, once step 1 and step 2 produce their inputs
- mock validation now, to show the final reporting path and a successful sample run

Any outputs generated from `mock_prediction_export.py` should be presented as
simulated or illustrative, not as real model performance.

The current illustrative sample run is already generated here:

- `reports/sample_fixture_run/benchmark/`
- `reports/sample_fixture_run/evaluation/`
- `reports/sample_fixture_run/mock_predictions.csv`

The sample run includes:

- a benchmark summary and review template
- a simulated prediction export that matches the step-2 contract
- JSON, Markdown, and HTML evaluation views
- slice metrics, confusion matrices, and top-confusion extracts

# Phase 7 Evaluation

This workspace contains a minimal evaluation harness for validating the query router/classifier on the 300-query sample.

## Workflow

1. Generate a hand-label template from the source CSV.
2. Review and fill in `gold_route` and `gold_short_circuit`.
3. Export classifier predictions from Foundry into CSV format.
4. Run the evaluator to produce metrics, a markdown summary, and an HTML dashboard.

## Expected Metrics

- Route accuracy
- Latency summary (`avg`, `p50`, `p95`, `max`)
- Token usage summary
- Total and average cost
- Correct short-circuit rate
- Supporting short-circuit precision and boolean accuracy
- Gold vs predicted route counts
- Confusion matrix

## Files

- `scripts/create_hand_label_template.py`: builds a review sheet from the source CSV.
- `scripts/evaluate_classifier.py`: joins labels and predictions, computes metrics, and writes reports.
- `scripts/mock_foundry_export.py`: generates a synthetic prediction export to smoke-test the pipeline.
- `scripts/create_hand_label_template.ps1`: PowerShell version of the template builder.
- `scripts/evaluate_classifier.ps1`: PowerShell version of the evaluator.
- `scripts/mock_foundry_export.ps1`: PowerShell version of the mock export generator.
- `templates/predictions_template.csv`: header template for Foundry exports.

## Hand-Label Template

Generate the template:

```powershell
./scripts/create_hand_label_template.ps1 `
  -Source "C:\Users\lenno\OneDrive\Documentos\300_queries.csv" `
  -Output templates\hand_label_template.csv
```

Fill in these columns:

- `gold_route`
- `gold_short_circuit`
- `label_status`
- `reviewer_notes`

The source route is copied into `seed_route` to speed up review, but the evaluator always prefers `gold_route` when present.

## Prediction Export Format

The evaluator accepts CSV with either `row_id` or `query` as the join key plus these fields:

- `predicted_route`
- `predicted_short_circuit` (optional; inferred from route if missing)
- `latency_ms` (optional)
- `prompt_tokens` (optional)
- `completion_tokens` (optional)
- `total_tokens` (optional)
- `estimated_cost_usd` (optional)
- `routing_path` (optional)
- `model` (optional)

## Evaluate

```powershell
./scripts/evaluate_classifier.ps1 `
  -Labels templates\hand_label_template.csv `
  -Predictions reports\mock_foundry_predictions.csv `
  -OutputDir reports
```

Outputs:

- `reports/evaluation_summary.json`
- `reports/evaluation_report.md`
- `reports/evaluation_dashboard.html`

## Smoke Test

Generate a synthetic Foundry-style export from the template:

```powershell
./scripts/mock_foundry_export.ps1 `
  -Labels templates\hand_label_template.csv `
  -Output reports\mock_foundry_predictions.csv
```

This is only for validating the evaluation pipeline. Replace it with a real Foundry export for production measurement.

The Python scripts are included as equivalent implementations, but this workspace was validated with the PowerShell versions because Python is not currently installed on the machine.
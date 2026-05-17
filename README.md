# Query Intent Resolver

This repository contains two completed workstreams for the Query Intent Resolver project:

1. **Part 1 - Phases 6 and 7**  
   Final modeling work for query-complexity classification.

2. **Part 2 - Step 3**  
   A standalone validation package for evaluating future classifier outputs on a held-out benchmark.

## Repository Structure

```text
.
|-- Part 1 - Phases 6 and 7/
|   |-- Data/
|   |-- final_outputs_complexity/
|   |-- train_complexity_primary.py
|   |-- FINAL_RESULTS.md
|   `-- README.md
|
`-- Part 2 - Step 3/
    |-- README.md
    `-- step3_validation/
        |-- scripts/
        |-- tests/
        |-- config/
        |-- fixtures/
        |-- templates/
        `-- reports/
```

## Part 1 Summary

The final Phase 6/7 direction is **complexity-first classification**:

- target classes: `short_circuit`, `medium`, `complex`, `llm_needed`
- primary model input: raw query text only
- best strict grouped-query accuracy: `0.816829`
- chosen model: word TF-IDF + character TF-IDF + lightweight query-pattern features with `LinearSVC`

The main limitation is label inconsistency in the raw data: `164` exact query strings have conflicting complexity labels, covering `1,365` rows.

Start here:

- [Part 1 README](./Part%201%20-%20Phases%206%20and%207/README.md)
- [Final Results](./Part%201%20-%20Phases%206%20and%207/FINAL_RESULTS.md)

## Part 2 Summary

Step 3 is a standalone validation workflow for future classifier exports. It:

- builds a fixed held-out benchmark
- validates persona and intent predictions
- derives route-tier and short-circuit behavior
- produces JSON, Markdown, HTML, CSV, and confusion-matrix outputs
- includes a mock dry-run path so the reporting pipeline can be demonstrated before real upstream inputs arrive

Start here:

- [Step 3 README](./Part%202%20-%20Step%203/README.md)
- [Validation Contract](./Part%202%20-%20Step%203/step3_validation/CONTRACT.md)

## Reproducibility Notes

- Phase 6/7 uses the raw CSV files in `Part 1 - Phases 6 and 7/Data/`.
- Step 3 is implementation-ready, but real validation results still depend on cleaned labels from step 1 and real classifier exports from step 2.
- Any outputs produced by the Step 3 mock generator are illustrative only and should not be presented as real model performance.

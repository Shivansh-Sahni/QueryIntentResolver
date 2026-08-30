# Manual Label Adjudication

The cleanup pipeline never guesses when the evidence for an exact query is weak or tied. Those cases are written to:

```text
v1/artifacts/data_cleanup/manual_review_queue.csv
```

## Review rule

Assign the **minimum handling tier that can answer the query correctly**:

- `short_circuit`: exact entity or directly indexed one-hop fact
- `medium`: normal retrieval, FAQ, or one-to-two-filter search
- `complex`: comparison, recommendation, ranking, multiple constraints, planning, or orchestration
- `llm_needed`: subjective, emotional, vague, or semantic interpretation needing a single LLM step

Safety rule: when uncertain between `short_circuit` and another class, do not choose `short_circuit`.

## Workflow

1. Open `manual_review_queue.csv`.
2. Fill `review_route`, `reviewer`, and `review_notes` for the rows being adjudicated.
3. Validate and merge the decisions:

```bash
python v1/scripts/apply_manual_review.py \
  --reviewed v1/artifacts/data_cleanup/manual_review_queue.csv \
  --overrides v1/data/manual_overrides.csv \
  --reviewer-required
```

4. Re-run the pipeline. The exact query will now resolve through `manual_override` with full audit provenance.

Never edit the frozen benchmark after viewing model results. An accepted benchmark-label correction requires a new benchmark version.

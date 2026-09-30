# Five-minute engineering demonstration

1. Open REVIEWER_BRIEF.html. State the exact engineering status and separate internal-quality/production gates shown by the executed report. Do not call the model production-proven.
2. Show the original reviewed CSV beside artifacts/data/review_audit.csv. Point out preserved reviewer notes, separately attributed corrections, context exclusions and the actual strict-training retention count.
3. Show artifacts/selection.json: model and thresholds chosen using grouped training OOF, not final test errors. Show the preserved old benchmark hash and original V1 snapshot.
4. Open comparison and applicability results. Show at least two failed examples, not only successes. Identify the core suite as assistant-authored and separate from real traffic. Explain the false-short-circuit denominator.
5. Start the API locally and call it with a new query, then add optional context and verify the unchanged response. Show blank/type/length rejection and /ready reporting production authorization false.
6. End with the concrete architecture decision sheet in INTEGRATION.md. Ask for route handlers and privacy-safe traffic, not a new open-ended project scope.

Reported results must come from current artifacts. Do not reuse the archived 93.30% figure as the result of this version. The old Qwen comparison measures its legacy model/parser/fallback combination; it does not discredit the contributor or make a general claim about large language models.

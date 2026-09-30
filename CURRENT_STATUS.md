# Current Status — Engineering Closeout

**Closeout date:** September 29, 2026, user-local date; CI execution is timestamped September 30 UTC.  
**Coordinator:** Shivansh Sahni.  
**Status:** standalone engineering/research deliverable complete; production-quality and deployment approval outstanding.

## Acceptance decision

Do not automatically promote V1.1. Its selected LinearSVC has 80.33% accuracy on the preserved 300-query regression benchmark but 9 false short circuits among 62 short-circuit predictions (14.52%), above the unchanged 5% ceiling. V1.0.1 remains the safer historical provisional reference at 2/42 (4.76%), although its recall is below target. Neither is production-authorized.

The V1.1 core applicability score is 62/100 on assistant-authored cases. The 20 stress cases are reported separately; they are not added to the core score to inflate performance. The paired historical accuracy improvement is 2.33 percentage points, with a row-bootstrap interval of -1.67 to +6.33 points. This does not establish a general gain.

## Completed assignments and evidence

| Work | Disposition | Evidence |
|---|---|---|
| Qwen inference/export | Anthony's original 300-row contribution retained; legacy model/parser/fallback comparison already scored | Original `v1/artifacts/models/qwen/` and issue #1 |
| Product scope | Tanvi's review accepted; the four-route query-only contract retained | Issue #4 and original contract |
| 55-query review submission | Received, identity-validated and processed; original notes unchanged | `v1_1/data/manual_review_received.csv`, `artifacts/data/review_audit.csv` |
| Review semantic consistency | 15 unchanged labels, 30 separately AI-policy-adjudicated, 10 deliberate context exclusions | `artifacts/data/review_summary.json`, `deferred_context.csv` |
| Missing applicability execution | Completed as AI-assisted tests, not independent teammate/user validation | 100 core + 20 stress cases and complete row-level outcomes |
| Runtime and packaging | 42 unit tests, 134 runtime checks, actual HTTP and Docker verification | `artifacts/verification/`, `FINAL_VALIDATION.json` |
| Model experiments | Logistic Regression, LinearSVC and SGD with grouped OOF selection; no test-tuned promotion | `artifacts/selection.json`, candidate reports |
| Presentation/handoff | HTML, Markdown, PDF, DOCX, decision sheet and demo script | `v1_1/docs/` |

Forty-five reviewed decisions enter the 7,916-row reviewed pool. Only 23 of those additions remain after the stricter exclusion protocol; the final fit uses 7,071 rows. Review completion does not imply every label was semantically correct or included in every model. Corrections are explicitly attributed to the AI-assisted closeout, not to Nimisha.

## Invariants verified

- Original `v1/` source, artifacts, model, benchmark, predictions and policy remain unchanged.
- Benchmark SHA-256: `591a31c4947d73fa7d77d2a94f32a69e689281c48a564d08317865b826bd84c6`.
- Original submitted review SHA-256: `0afa8eef4c9c0d897a1adb0c6c29b8b536b3715ab194b935540faedbc1c884aa`.
- Applicability suite hash frozen before closeout inference; no post-result relabeling.
- Model/threshold selection uses grouped training OOF only. Full feature fitting is inside grouped calibration.
- Exact and declared lexical template-family overlap between the new fit and historical benchmark: zero. This is not proof of zero semantic similarity.
- Optional persona/page/filters/context/session do not alter output.
- Guard/fallback confidence is not presented as certainty about a different discarded class.
- No external model API calls in the closeout; unknown hosting and downstream costs are not reported as zero.

## Deliberately still open

**Model quality:** the selected candidate fails the short-circuit safety target. Any further model or label-policy changes require a new declared experiment and genuinely separate development/validation evidence, not tuning this benchmark until it looks good.

**MascotGO/product integration:** actual invocation surfaces, route bindings, supported indexed facts/entity disambiguation, optional request fields, hosting, authorized real-query/shadow data and acceptance tolerances require product-owner decisions. Issue #5 remains open. No endpoint or deployment is invented.

## Single handoff path

Start with [release decision](v1_1/docs/RELEASE_DECISION.md), then [reviewer brief](v1_1/docs/REVIEWER_BRIEF.html), [full technical report](v1_1/docs/TECHNICAL_CLOSEOUT.md), [integration boundary](v1_1/docs/INTEGRATION.md), and [executed summary](v1_1/artifacts/SUMMARY.json).

No unfinished contributor response is treated as a dependency for the completed standalone deliverable. No absent contributor is credited with new testing they did not perform. The remaining safety and product gates are visible, not silently closed.

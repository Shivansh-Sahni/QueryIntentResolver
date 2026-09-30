# Release Decision: Engineering Delivered, No Automatic Promotion

The standalone engineering handoff is complete. The production-quality objective is not. Do not automatically promote V1.1: it falsely short-circuited 9 of 62 predicted short circuits (14.52%), versus 2 of 42 (4.76%) for the preserved V1.0.1 reference. Keep the original reference for comparison and V1.1 for research/integration review. Neither is authorized for live traffic.

## Evidence, not a deadline-driven release

The observed V1.1 accuracy gain is 2.33 percentage points on the old 300-query regression benchmark, but its paired row-bootstrap 95% interval is -1.67 to 6.33 points. Training conditions differ: V1.1 excludes heuristic template families present in that benchmark. This does not establish a general improvement. The balanced assistant-authored core applicability suite achieved 62.00%; it is not independent real-user validation.

## Completed internal deliverables

- All 55 received review rows matched original quarantine identities. 15 labels were retained, 30 separately AI-policy-adjudicated, and 10 context-dependent rows deliberately excluded. Original reviewer values remain intact.
- Three fixed candidates were evaluated using training-only grouped OOF selection and nested grouped calibration. The selected policy was saved before evaluation labels were read.
- Applicability execution, error reporting, 42 unit tests, 134 runtime checks, actual HTTP smoke testing and a Docker build/inference test are complete.
- Reproducible source, candidate model, hashes, full predictions, review audit, documentation and presentation files are delivered.

## Not represented as complete

The candidate does not meet the unchanged short-circuit safety target. Independent real traffic, actual MascotGO route bindings, supported index fields, acceptance tolerances and deployment authorization remain unfulfilled. Issue #5 is the external architecture decision record; the model-quality risk is separately retained here rather than falsely relabeled as an external-only dependency.

## Presentation order

1. This release decision.
2. REVIEWER_BRIEF.html and EXECUTIVE_HANDOFF.pdf.
3. TECHNICAL_CLOSEOUT.md, model comparison and applicability failures.
4. Local CLI/API demonstration.
5. INTEGRATION.md: concrete MascotGO decisions.

All v1/ files are preserved. No model, threshold, parser or test label changed in this presentation pass.

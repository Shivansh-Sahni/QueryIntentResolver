# Changelog

## 1.0.1 — 2026-09-02

- Added a dated project-status record with verified data, benchmark, model-safety, latency, automation, and validation evidence.
- Added a complete repository index separating the active V1 implementation from historical Phase 6/7 and Step 3 work.
- Clarified that the current model recommendation remains provisional pending the Qwen comparison, independent label review, natural-query testing, and real-traffic validation.
- Documented why the higher-accuracy raw diagnostic model is not release-eligible due to excessive false short-circuiting.
- Changed model comparison so diagnostic entries can never be recommended or packaged.
- Added explicit separation between the recommended release model and the highest analytical score.
- Added release validation requiring the packaged model to be real, benchmark-verified, full-coverage, and identical to the recommendation.
- Assigned concrete, bounded team deliverables for Qwen evaluation, label review, API/applicability testing, and product-scope confirmation.
- Consolidated the exact MascotGO integration decisions still required from Peter.
- Removed the obsolete one-time source-bootstrap workflow.
- Reduced automatic workflow triggers to relevant code, configuration, data, and dependency changes.
- Made the costly zero-shot baseline opt-in through manual workflow dispatch.
- Added safe fetch/rebase/retry logic for generated-artifact commits to prevent non-fast-forward failures when another commit lands during a build.
- Verified the replacement GitHub Actions run passed tests, model build, release packaging, artifact upload, validation, and generated-artifact publication.
- Preserved the frozen V1 contract and benchmark without changing benchmark labels or model claims.

## 1.0.0 — 2026-08-30

- Froze the raw-query-only route contract.
- Standardized the four route labels.
- Added conflict-aware data cleanup with provenance and manual-review quarantine.
- Added a deterministic, immutable, query-disjoint benchmark.
- Added calibrated LinearSVC training and safety-aware deployment policy.
- Added deterministic, zero-shot, API-LLM, and Anthony-Qwen evaluation paths.
- Added safety-weighted model shootout and release packaging.
- Added Python, CLI, FastAPI, Docker, OpenAPI, and JSON Schema interfaces.
- Added integrity validation and automated GitHub Actions execution.

# Changelog

## 1.0.1 — 2026-09-02

- Added a dated project-status record with verified data, benchmark, model-safety, latency, and validation evidence.
- Clarified that the current model recommendation remains provisional pending the Qwen comparison and real-query validation.
- Documented why the higher-accuracy raw diagnostic model is not release-eligible due to excessive false short-circuiting.
- Assigned concrete, bounded team deliverables for Qwen evaluation, label review, API/applicability testing, and product-scope confirmation.
- Consolidated the exact MascotGO integration decisions still required from Peter.
- Preserved the frozen V1 contract and benchmark without changing model results.

## 1.0.0 — 2026-08-30

- Froze the raw-query-only route contract.
- Standardized the four route labels.
- Added conflict-aware data cleanup with provenance and manual-review quarantine.
- Added a deterministic, immutable, query-disjoint benchmark.
- Added calibrated LinearSVC training and safety-aware deployment policy.
- Added deterministic, zero-shot, API-LLM, and Anthony-Qwen evaluation paths.
- Added safety-weighted model shootout and release packaging.
- Added Python, CLI, FastAPI, Docker, and JSON Schema interfaces.
- Added integrity validation and automated GitHub Actions execution.

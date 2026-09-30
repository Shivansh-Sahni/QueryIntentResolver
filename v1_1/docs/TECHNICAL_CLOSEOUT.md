# Query Intent Resolver — Technical Closeout

**Engineering delivery:** complete, with reproducible source, artifacts, review audit, runtime, tests, evaluation, documentation, and integration seam.  
**Internal model quality gates:** NOT ALL MET.  
**Production deployment:** not authorized; requires MascotGO bindings, product approval, independently labeled real queries, and acceptable operational risk.

## Explicit promotion decision

The standalone engineering handoff is complete. The production-quality objective is not. Do not automatically promote V1.1: it falsely short-circuited 9 of 62 predicted short circuits (14.52%), versus 2 of 42 (4.76%) for the preserved V1.0.1 reference. Keep the original reference for comparison and V1.1 for research/integration review. Neither is authorized for live traffic.

## Decision for the handoff

The OOF-selected V1.1 candidate is **linearsvc**, with short-circuit threshold **0.6** and lookup-rule override **False**. It was selected using only grouped training out-of-fold results; the historical benchmark and new applicability labels were not used to choose the candidate or threshold. Completing the engineering work does not waive the predeclared quality gates.

The original V1.0.1 source, trained artifact, benchmark, predictions and policy remain byte-for-byte preserved. V1.1 is delivered beside them, not silently substituted for the earlier model. Neither model is declared authorized for live user traffic by this handoff.

## Source and contribution closeout

Nimisha's submitted review has **55** rows and matches all quarantined query IDs. It is retained unchanged in `data/manual_review_received.csv`. Structural completion was confirmed, but a semantic consistency pass identified conflicting routes across otherwise equivalent school/program substitutions. A completed form was therefore not treated as automatically correct training truth.

- **15** labels retained unchanged under the explicit closeout policy.
- **30** labels separately adjudicated by the AI-assisted closeout pass, with row-level rationale and original label/notes retained.
- **10** context-dependent queries retained outside supervised training.

No modified opinion is attributed to Nimisha. The audit is `artifacts/data/review_audit.csv`; exclusions are `artifacts/data/deferred_context.csv`. Context-dependent cases are a deliberate modeling boundary, not a missing submission.

Anthony supplied the original Qwen inference export through PR #6. The original export and legacy scores are preserved. Tanvi completed the product-scope review in issue #4. Remaining applicability execution was completed in this closeout as **AI-assisted testing**, not described as a new independent teammate review. Historical phase contributors retain credit in the repository history.

## Data and leakage controls

The reviewed training pool contains **7916** rows. The strict V1.1 fit uses **7071** rows after excluding **845** rows in heuristic template families represented in the historical benchmark. Of the newly reviewed examples, **23** remain in this stricter fit; accepting a review into the versioned data pool is not the same as using it in every fitted model.

There are **0 exact-query overlaps** and **0 family overlaps under the declared lexical heuristic** between the V1.1 fit and the historical benchmark. This heuristic replaces known schools, programs, places and numbers; it is not a proof of zero semantic similarity. The legacy training pool overlapped **46** such benchmark families. The two versions consequently do not have identical training conditions.

Grouped outer cross-validation has three folds. Each calibrated estimator fits its entire feature pipeline inside three grouped inner folds: vocabulary construction is not performed globally before calibration. The frozen protocol defines three candidates, a fixed threshold grid and a restricted full-match lookup grammar. The rule layer is disabled unless its training-only evidence satisfies the declared support and precision criteria.

The 300-row V1 benchmark is balanced (75 per route). It has been observed repeatedly in this project's history, so this is **historical regression evidence**, not a newly blind final test. It was not relabeled. Its SHA-256 remains `591a31c4947d73fa7d77d2a94f32a69e689281c48a564d08317865b826bd84c6`.

## Historical benchmark comparison

| System | Accuracy | Macro F1 | False SC among predicted SC | SC recall |
|---|---:|---:|---:|---:|
| v1_0_1 | 78.00% | 0.7784 | 4.76% (2/42) | 53.33% |
| qwen_legacy_pipeline | 27.33% | 0.1771 | 16.67% (1/6) | 6.67% |
| V1.1 selected: linearsvc | 80.33% | 0.8041 | 14.52% (9/62) | 70.67% |

The V1.1 accuracy Wilson 95% interval is **75.46%–84.44%**. The false-short-circuit discovery interval is **7.83%–25.34%**. Small denominators limit certainty even where point estimates look favorable.

In this project, the legacy field `false_short_circuit_rate` means **false discoveries / predicted short circuits**. It is not the usual false-positive rate over actual non-short queries. V1.1 also reports the latter (**4.00%**) and the all-query fraction (**3.00%**). A zero predicted-short denominator is reported as undefined, never as guaranteed zero risk.

The Qwen result describes its then-existing persona/intent generation, parser, fallback, and deployment policy together. It does not establish that the underlying Qwen architecture is unsuitable for direct route training. The recorded GPU generation latency and local CPU classifier timings are not a controlled cross-hardware speed comparison. The old Qwen zero-cost field was an unpriced default, not evidence of free compute.

## Applicability and robustness

A separate **120-case** suite was authored and hashed before closeout inference: **100 balanced core cases**, plus **20 boundary/stress cases**. These are assistant-authored, policy-labeled examples, not real MascotGO traffic or independent human validation. Assumptions are visible per case. No failed case was relabeled or used for model selection after predictions.

| Set | Rows | Accuracy | Macro F1 | False SC discoveries | SC recall |
|---|---:|---:|---:|---:|---:|
| Core | 100 | 62.00% | 0.6175 | 20.00% | 64.00% |
| Stress | 20 | 90.00% | 0.2368 | not defined | not defined |

The stress set predominantly expects clarification/escalation; do not combine it with the core set to inflate the headline. There are **1** exact training overlaps in the full suite. A core exact-novel subset and full overlap audit are supplied. Novelty is not inferred simply because a sentence was typed anew.

Capitalization, whitespace and punctuation variants are tested separately. Full row-level outputs, failure examples, route confusion, confidence reliability and metamorphic stability are in `artifacts/applicability/`. The limited unsupported-language/instruction-pattern guard is a routing heuristic, not a comprehensive security or out-of-domain detector. `llm_needed` is a request for further handling/clarification, not permission to fulfill unsafe content or proof that one model call will suffice.

## Runtime and integration

Successful `POST /v1/resolve` returns exactly `route` and `confidence`. Optional persona, page, filters, context and session are accepted but do not affect the result. Invalid types, blank input, excessive length, unsupported control characters and oversized batches are rejected. `/health` means the service process is available; `/ready` means the model is loaded, not that production approval exists.

For learned decisions, confidence is the probability assigned to the **emitted** route, not the top probability of a different route before fallback. Guarded inputs return zero confidence to signal unknown. Any enabled rule uses a separately estimated training-only precision signal. These meanings are documented rather than presented as calibrated guarantees across all decision sources.

The runtime performs no network calls, no database mutations, and no raw-query logging. API-key authentication is optional for local evaluation and required at the deployment gateway for any externally exposed installation. Trusted bundle hashes are checked before model loading; this does not make untrusted pickle/joblib files safe. The supplied environment is pinned.

**134/134 runtime verification checks passed**. The in-process 1,000-query serial test processed approximately **177.8 queries/second**. That is a measured local CPU workload, not an HTTP/network/production service-level agreement. Threaded parity is separately verified.

`RouterBindings` accepts explicit callables for all four routes and fails when a binding is missing. The deployment preflight remains false until the product owner approves concrete handlers, real traffic has been validated and the quality gates are satisfied. No fabricated endpoint or claimed Foundry deployment is included.

## Cost and operational evidence

This closeout made **0 external model API calls**. The local classifier consumes no LLM tokens. Hosting, CPU, monitoring, data lookup and downstream execution costs are not measured and must not be reported as zero. Historical Phase 5 pricing tables are planning material, not contemporary measured costs. `config/cost_model.example.json` provides explicit replaceable assumptions rather than a savings claim.

## What remains outside this completed engineering delivery

Peter/MascotGO must provide the actual invocation surface, route-to-handler mapping, optional request fields, deployment boundary, authorized data/index coverage, and a privacy-safe real-query or shadow-traffic sample. A product owner must accept routing-error tolerances. These remain tracked by issue #5; they cannot be invented or completed on MascotGO's behalf.

The internal handoff can be designated complete. Production validation/deployment cannot. If the internal gate status at the top is not all met, the candidate remains provisional and must not be promoted merely because a deadline expired.

## Reproducibility

Run `PYTHONPATH=v1_1 python -m qir_release.build --repo-root .` using `v1_1/requirements.txt`. The selected policy is saved before evaluation labels are opened. Its hash is recorded on every candidate report. The baseline snapshot checks every file under `v1/` before and after the build. Reproduction must fail if the benchmark or applicability suite changes unexpectedly.

## Technical references and source basis

- Original Google Drive project plan: https://docs.google.com/document/d/1NKtirKNjp--RUNvo2KindbX4F-p1Ceir-dGA9BnIg70/edit (original phases 1–7; read during closeout; broader persona/intent outputs were later narrowed by the team).
- Current contract and original data provenance: `v1/CONTRACT.md`, `v1/ROUTING_LABEL_POLICY.md`, original phase directories, and Git history.
- scikit-learn calibration API: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
- Grouped validation API: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
- Microsoft Foundry OpenAPI tool integration: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/openapi (integration pattern only, not a deployment claim).
- GitHub build artifacts: https://docs.github.com/en/actions/tutorials/store-and-share-data

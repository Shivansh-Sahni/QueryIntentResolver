# Query Intent Resolver V1 — Current Status

**Updated:** September 14, 2026  
**Technical coordinator:** Shivansh Sahni  
**Active release:** `qir-v1.0.1`  
**Frozen benchmark:** `qir-v1.0.0`

## Current conclusion

V1 is implemented, reproducible, and ready for product-integration review. The current provisional release recommendation remains the calibrated query-only LinearSVC with the frozen deployment safety policy.

The product scope has now been independently confirmed, the Qwen comparison has been completed and scored, and the remaining active work is limited to label adjudication, natural-query applicability testing, real-traffic validation, and MascotGO route binding.

## Frozen contract

Input:

```json
{
  "query_text": "UCLA vs USC for engineering"
}
```

Output:

```json
{
  "route": "complex",
  "confidence": 0.91
}
```

Valid routes:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

Persona, page, filters, prior messages, and session context remain optional and decoupled.

## Verified dataset and benchmark

- Raw contributed rows: **11,575**
- Unique normalized queries: **8,226**
- Cleaned/resolved unique queries: **8,171**
- Unresolved unique queries quarantined: **55**
- Training queries: **7,871**
- Frozen benchmark rows: **300**
- Benchmark balance: **75 per route**
- Exact normalized-query train/benchmark overlap: **0**
- Manual-review leakage into training: **0**
- Qwen blind-input gold-label leakage: **0**
- Release, benchmark, model, and policy hashes: **verified**

## Current recommended model

`calibrated_word_char_shape_linearsvc`

- Accuracy: **78.00%**
- Macro F1: **0.7784**
- False short-circuit rate: **4.76%**
- Short-circuit precision: **95.24%**
- Short-circuit recall: **53.33%**
- P95 local latency: approximately **4.26 ms/query**
- Marginal local inference API cost: **$0**

The model passes the accuracy, macro-F1, and false-short-circuit safety floors. It remains provisional because short-circuit recall is below the frozen 65% release requirement.

## Qwen comparison — completed

Anthony completed inference on all 300 blind benchmark rows. The initial scoring blocker came from free-form intent outputs that did not match the strict intent parser. To avoid post-hoc tuning after benchmark outputs had been observed, the repository now scores `predicted_route_raw` as the Qwen system's actual end-to-end routing output. No generation settings, fuzzy intent mapping, or benchmark-driven parser correction was applied.

`anthony_qwen2_5_3b_lora_intent_to_route`

- Coverage: **300/300**
- Accuracy: **27.33%**
- Macro F1: **0.1771**
- False short-circuit rate: **16.67%**
- Short-circuit recall: **6.67%**
- Mean latency: approximately **1,516 ms/query**
- P95 latency: approximately **4,151 ms/query**

Conclusion: the current persona/intent Qwen model does not transfer effectively to the four-route V1 task. Any direct four-route Qwen redesign belongs in a versioned V1.1 experiment using a new development set; it must not be tuned against the frozen V1 benchmark.

Tracking issue #1 is complete and closed.

## Product review — completed

Tanvi independently reviewed the V1 status, contract, and handoff. Her findings confirm that:

- raw-query-to-routing-complexity is the correct V1 objective;
- the four route labels are sufficient for the current scope;
- no other required product change was identified;
- the remaining product requirement is defining the concrete downstream handler for each route.

Tracking issue #4 is complete and closed.

## Active work

### Shivansh — integration, scoring, release, and coordination

- maintain the frozen contract and benchmark;
- integrate reviewed label decisions without modifying the benchmark;
- analyze natural-query failures;
- maintain the API, CI, release artifacts, and documentation;
- obtain MascotGO route bindings and deployment decisions from Peter;
- prepare the next version only after the remaining evidence is complete.

### Nimisha — unresolved-label adjudication

Issue #2: review the 55 quarantined unique queries using `ROUTING_LABEL_POLICY.md`.

Required output per query:

- proposed route;
- one-sentence rationale;
- confidence: `high`, `medium`, or `context_dependent`;
- reviewer name.

This improves a future training version but does not alter the frozen V1 benchmark.

### Ridhi — natural-query/API applicability testing

Issue #3: execute the primary 25-query natural-language test covering all four routes, typos, shorthand, incomplete phrasing, and conversational requests.

Required fields:

- query text;
- expected route;
- actual route;
- confidence;
- pass/fail;
- failure note.

### Anika — independent review and backup for issue #3

Review the expected labels and the failed or borderline cases from Ridhi's test. If Ridhi is unavailable, complete the primary test log.

### Tanvi — completed

Product-scope review is complete. No further blocking task is currently assigned.

### Anthony — completed

Qwen inference and benchmark export are complete. No rerun is currently required.

### Edward — removed from the active plan

Edward has not been active in the project for approximately three months. His applicability-testing task has been reassigned to Ridhi, with Anika as reviewer/backup.

## Decisions still required from Peter

1. Which product surfaces invoke the resolver first: search bar, chat, GO button, or all three?
2. What downstream handler does each route call?
3. Which optional context fields can the application reliably supply?
4. Can the team receive a privacy-safe real-query sample or shadow-mode feed?
5. Should the resolver deploy as a backend module, standalone FastAPI service, or Microsoft Foundry action?

These decisions are tracked in issue #5.

## Current open issues

- #2 — unresolved-label adjudication
- #3 — natural-query and API applicability testing
- #5 — MascotGO integration decisions

Completed:

- #1 — Qwen benchmark comparison
- #4 — product-scope review

## Automation status

The latest GitHub Actions run completed successfully and:

- passed all automated tests;
- rebuilt data-cleanup artifacts;
- preserved the frozen benchmark;
- scored the Qwen export;
- reran the model shootout;
- regenerated the release;
- validated model eligibility and hashes;
- uploaded the release artifact;
- committed generated artifacts back to `main`.

## Guardrails

- Never edit or relabel the frozen benchmark after observing predictions.
- Never tune a model or parser against frozen-benchmark errors.
- Never present mock or adapted results as real performance.
- Never package a diagnostic model as the release recommendation.
- Keep archived experimental metrics separate from canonical V1 metrics.
- Route-semantic or benchmark changes require a new version.

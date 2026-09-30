# Source register and requirements traceability

## Sources consulted

- Live repository at base commit d2801dbd292c71c0bedc7fa06172ac5c7a1c5557: source, contracts, policies, benchmark, model exports, issue records and historical work.
- Original Drive project plan, ID 1NKtirKNjp--RUNvo2KindbX4F-p1Ceir-dGA9BnIg70: original phases 1–7 and February/March contributor updates. The source was read, including its update tabs. Its old dates and broad persona/intent objective are not mistaken for the later frozen V1 contract.
- manual_review_completed.csv, supplied by Shivansh as Nimisha's submission: original bytes copied to data/manual_review_received.csv.
- Previously uploaded Phase 4 findings and Phase 5 routing strategy: historical design evidence. Pricing and latency estimates in the March planning draft are not measured contemporary operating costs. Private/confidential draft documents are not republished here.
- Issue #4: Tanvi's completed product-scope review. Issue #1 and PR #6: Anthony's Qwen inference and parser issue report. Issue #5: external MascotGO architecture decisions, unresolved in the read repository records.

The accessible Drive search returned the original project-plan document, not a current approved production route map. Lack of a new specification in these accessible sources is not a claim that no such document exists anywhere.

## Original requirement to present deliverable

| Requirement | Closeout evidence | Boundary |
|---|---|---|
| Persona and intent taxonomy | Historical phase documents, canonical V1 route policy, retained source metadata | Persona/intent output decoupled by the later team decision; no demographic inference added. |
| Thousands of labeled queries, Python-ready export | Original contributor CSVs, reviewed pool and strict-training CSV | Mostly generated/curated supervision; no claim of real user distribution. |
| Fast vs complex routing | Explicit four-label contract, deployment policy and binding interface | Actual MascotGO handler mapping requires product approval. |
| Classifier implementation | Three fixed lightweight candidates, grouped calibration and runtime bundle | Candidate/threshold selected on training OOF only. |
| Evaluation and dashboard | Preserved 300-row regression benchmark, 120-case diagnostic suite, full errors, reviewer brief | Applicability is assistant-authored, not independent; old test already observed. |
| Confidence and fallbacks | Emitted-class confidence, conservative SC gate, guard-unknown confidence | Not a correctness guarantee or proof of downstream sufficiency. |
| Latency and cost | Measured same-run CPU timing, API checks, zero external LLM calls, unpriced cost inputs | Infrastructure and downstream costs are unknown. |
| Engineering handoff | Pinned dependencies, CLI/API/OpenAPI/Docker, tests, manifests, PDF/DOCX/HTML | No credentials, actual route bindings or live authorization invented. |

## Attribution

Shivansh coordinated the closeout and supplied direction. Nimisha supplied the review CSV, Anthony supplied Qwen inference, and Tanvi supplied the product review. Historical source contributions remain credited in Git history and original phase records. Code, additional semantic adjudication, diagnostic tests and documentation in this closeout are AI-assisted work produced for Shivansh. This is not independent labor or review by absent teammates.

## Evidence retention

All v1/ files are hashed before and after the build. Original review bytes are immutable. New labels have explicit sources. New candidate results never replace historical benchmark labels. No unsupported V1.2 achievement is promoted from chat history; prior experimental work stays separately labeled under research_archive/.

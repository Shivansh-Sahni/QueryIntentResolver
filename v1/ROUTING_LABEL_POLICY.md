# Query Intent Resolver V1 — Routing Label Policy

## Frozen V1 objective

Given raw `query_text`, predict the minimum handling tier needed to answer the query correctly.

Valid output labels are exactly:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

The production model input is raw query text only. Persona, intent, current page, filters, conversation history, and other session context are intentionally excluded from V1 model input. They may be added later without changing this contract.

## Canonical label definitions

### `short_circuit`
Use when the query can be handled deterministically without an LLM or multi-step reasoning.

Typical cases:
- exact school/entity lookup: `MIT`
- one-hop factual attribute lookup when the value is directly indexed: `UCLA tuition`
- direct deterministic lookup/filter with no semantic interpretation needed

### `medium`
Use when the query needs ordinary search/retrieval or lightweight processing, but not open-ended reasoning or multi-step orchestration.

Typical cases:
- one or two structured filters: `colleges in California`
- admissions/process facts: `Stanford application deadline`
- financial-aid/career-outcome factual searches
- B2B product/documentation questions that route to a normal product/support pipeline

### `llm_needed`
Use when a single LLM/rewrite/semantic-interpretation step is needed, but a multi-step agent workflow is not.

Typical cases:
- subjective or vague fit questions: `schools with normal people`
- emotional/advisory questions
- ambiguous natural-language interpretation where a lightweight semantic search is insufficient

### `complex`
Use when the query requires multiple constraints, comparison/ranking, recommendation, planning, or multi-step reasoning/orchestration.

Typical cases:
- multi-constraint search: `affordable engineering schools in California with good job placement`
- comparison: `UCLA vs USC for engineering`
- recommendation/ranking: `schools like Stanford but cheaper`
- multi-step strategy or workflow requests

## Intent-to-route adjudication map

Intent is **not** an input to the V1 classifier. It is used only as annotation metadata to repair noisy historical complexity labels.

| Intent | Canonical route |
| --- | --- |
| `exact_lookup` | `short_circuit` |
| `attribute_lookup` | `short_circuit` |
| `filtered_search` | `medium` |
| `admissions_process` | `medium` |
| `cost_financial_aid` | `medium` |
| `career_outcomes` | `medium` |
| `b2b_partnership` | `medium` |
| `multi_constraint` | `complex` |
| `comparison` | `complex` |
| `recommendation` | `complex` |
| `strategy` | `complex` |
| `analytics_request` | `complex` |
| `rewrite_needed` | `complex` |
| `advisory` | `llm_needed` |
| `emotional_advisory` | `llm_needed` |
| `reflective_advisory` | `llm_needed` |
| `campus_life_fit` | `llm_needed` |
| `profile_management` | `medium` |

Unknown intents are not guessed. They are resolved by duplicate-vote evidence when strong enough; otherwise they are sent to manual review.

## Conflict-resolution hierarchy

For each normalized exact query:

1. **Valid-label normalization** — normalize spelling/spacing/case and drop invalid labels such as the historical `high` value.
2. **Intent policy** — if the query's mapped intent metadata unanimously implies one canonical route, use that route.
3. **Strong majority** — otherwise use the observed complexity majority only when the top label has at least 67% of votes and a margin of at least 2 rows over the runner-up.
4. **Manual review** — do not invent a label when evidence is weak or tied. Exclude the query from model training until adjudicated.

This policy is intentionally conservative. Removing a small number of genuinely ambiguous training examples is preferable to encoding contradictory supervision into every model in the V1 shootout.

## Leakage rule

All rows sharing the same normalized query must stay in the same partition. No normalized query may appear in both training and the frozen benchmark.

# Query Intent Resolver V1 Routing Label Policy

## Frozen objective

Given raw query text, predict the minimum handling tier required to answer the query correctly.

Valid labels are exactly:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

Persona, intent, page, filters, conversation history, and account context are not model inputs in V1. Historical intent labels may be used only to repair contradictory training annotations.

## Canonical definitions

### `short_circuit`

The query can be handled deterministically without an LLM or multi-step reasoning.

Examples:

- `MIT`
- `UCLA tuition`
- `Stanford acceptance rate`

### `medium`

The query requires ordinary search, retrieval, or lightweight processing but not open-ended reasoning or multi-step orchestration.

Examples:

- `colleges in California`
- `Stanford application deadline`
- `schools with high internship placement rates`
- `pricing for partner colleges`

### `complex`

The query requires comparison, ranking, recommendation, multiple constraints, planning, or multi-step orchestration.

Examples:

- `UCLA vs USC for engineering`
- `schools like Stanford but cheaper`
- `affordable engineering schools in California with good job placement`

### `llm_needed`

The query requires subjective interpretation, ambiguity resolution, emotional guidance, advisory reasoning, or a natural-language rewrite before ordinary retrieval can proceed.

Examples:

- `schools with normal people`
- `colleges where people do not care about football`
- `what school would feel right for me`

## Historical intent-to-route map

| Intent | Canonical route |
| --- | --- |
| `exact_lookup` | `short_circuit` |
| `attribute_lookup` | `short_circuit` |
| `filtered_search` | `medium` |
| `admissions_process` | `medium` |
| `cost_financial_aid` | `medium` |
| `career_outcomes` | `medium` |
| `b2b_partnership` | `medium` |
| `profile_management` | `medium` |
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

## Conflict-resolution order

For each normalized exact query:

1. Apply an explicit reviewed override when one exists.
2. Accept a unanimous valid historical route.
3. If all recognized historical intents map to one route, apply that policy route.
4. Accept an observed-route majority only when it has at least 67 percent of votes and a margin of at least two rows.
5. Accept an intent-derived majority only when it has at least 75 percent of votes and a margin of at least two rows.
6. Otherwise export the query for manual review and exclude it from training and benchmark selection.

No weak or tied conflict is silently resolved.

## Benchmark rule

All copies of one normalized query must remain in one partition. No normalized query may appear in both training and benchmark data. Once the benchmark manifest is produced, benchmark membership and labels are frozen.

## Deployment confidence policy

- Confidence below `0.45`: route to `llm_needed`.
- A `short_circuit` prediction below `0.80`: escalate to `medium`.
- Unknown output labels: route to `llm_needed`.

These rules prioritize avoiding dangerous false short circuits over saving a marginal amount of compute.

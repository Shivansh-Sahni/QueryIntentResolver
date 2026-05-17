# Step 3 Evaluation Report

## Dataset Coverage
- Labels: 12
- Matched predictions: 12
- Missing predictions: 0
- Matched by row_id: 12
- Matched by query fallback: 0
- Join method distribution: row_id=12

## Core Metrics
- Persona accuracy: 100.0%
- Intent accuracy: 100.0%
- Joint accuracy: 100.0%
- Route-tier accuracy: 100.0%
- Short-circuit precision: 100.0%
- Short-circuit recall: 100.0%
- Short-circuit boolean accuracy: 100.0%

## Latency
- Average latency: 964.00 ms
- P50 latency: 771.00 ms
- P95 latency: 1645.70 ms
- Max latency: 1649.00 ms

## Tokens And Cost
- Average total tokens: 262.92
- Total tokens: 3155.00
- Total cost: $0.003787
- Average cost per query: $0.000316

## Acceptance Status
- Overall status: PASS

| Metric | Actual | Threshold | Passed |
| --- | --- | --- | --- |
| intent_accuracy | 100.0% | 90.0% | yes |
| persona_accuracy | 100.0% | 85.0% | yes |
| joint_accuracy | 100.0% | 80.0% | yes |
| route_tier_accuracy | 100.0% | 90.0% | yes |
| short_circuit_precision | 100.0% | 95.0% | yes |

## Route Tier Distribution
- agentic: 9
- short_circuit: 2
- standard_search: 1

## Confidence Bands
- 0.85-1.00: count=8, intent_accuracy=100.0%, route_tier_accuracy=100.0%
- 0.65-0.84: count=4, intent_accuracy=100.0%, route_tier_accuracy=100.0%
- 0.40-0.64: count=0, intent_accuracy=0.0%, route_tier_accuracy=0.0%
- <0.40: count=0, intent_accuracy=0.0%, route_tier_accuracy=0.0%

## Operating Counts
- Proceed high-confidence: 8
- Proceed medium-confidence: 4
- Escalate low-confidence: 0
- Fallback insufficient-confidence: 0
- Fallback unknown-intent: 0

## Routing Health
- Route-mapping fallback threshold: 0.40
- Unknown predicted intent count: 0
- Unknown predicted intents: none

## Recommendations
- Intent accuracy meets the 90% baseline. Keep the current schema unless repeated confusion pairs remain operationally costly.

## Worst-Performing Personas
| Persona | Count | Accuracy |
| --- | --- | --- |
| advisor | 3 | 100.0% |
| high_school_student | 3 | 100.0% |
| counselor_teacher | 2 | 100.0% |
| parent | 2 | 100.0% |
| college_b2b | 1 | 100.0% |

## Worst-Performing Intents
| Intent | Count | Accuracy |
| --- | --- | --- |
| admissions_process | 1 | 100.0% |
| attribute_lookup | 1 | 100.0% |
| b2b_partnership | 1 | 100.0% |
| campus_life_fit | 1 | 100.0% |
| career_outcomes | 1 | 100.0% |
| comparison | 1 | 100.0% |
| cost_financial_aid | 1 | 100.0% |
| exact_lookup | 1 | 100.0% |

## Top Persona Confusions
- None

## Top Intent Confusions
- None

## Persona Confusion Matrix
| Gold \ Predicted | advisor | college_b2b | college_student | counselor_teacher | high_school_student | parent |
| --- | --- | --- | --- | --- | --- | --- |
| advisor | 3 | 0 | 0 | 0 | 0 | 0 |
| college_b2b | 0 | 1 | 0 | 0 | 0 | 0 |
| college_student | 0 | 0 | 1 | 0 | 0 | 0 |
| counselor_teacher | 0 | 0 | 0 | 2 | 0 | 0 |
| high_school_student | 0 | 0 | 0 | 0 | 3 | 0 |
| parent | 0 | 0 | 0 | 0 | 0 | 2 |

## Intent Confusion Matrix
| Gold \ Predicted | admissions_process | attribute_lookup | b2b_partnership | campus_life_fit | career_outcomes | comparison | cost_financial_aid | exact_lookup | filtered_search | multi_constraint | recommendation | rewrite_needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admissions_process | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| attribute_lookup | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| b2b_partnership | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| campus_life_fit | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| career_outcomes | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| comparison | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| cost_financial_aid | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| exact_lookup | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| filtered_search | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| multi_constraint | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| recommendation | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| rewrite_needed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

## Route Tier Confusion Matrix
| Gold \ Predicted | agentic | short_circuit | standard_search |
| --- | --- | --- | --- |
| agentic | 9 | 0 | 0 |
| short_circuit | 0 | 2 | 0 |
| standard_search | 0 | 0 | 1 |

## Highest Confidence Wrong Predictions

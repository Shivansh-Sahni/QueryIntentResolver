# Step 3 Evaluation Report

## Dataset Coverage
- Labels: 18
- Matched predictions: 18
- Missing predictions: 0
- Matched by row_id: 18
- Matched by query fallback: 0
- Join method distribution: row_id=18

## Core Metrics
- Persona accuracy: 88.9%
- Intent accuracy: 94.4%
- Joint accuracy: 83.3%
- Route-tier accuracy: 100.0%
- Short-circuit precision: 100.0%
- Short-circuit recall: 100.0%
- Short-circuit boolean accuracy: 100.0%

## Latency
- Average latency: 1065.17 ms
- P50 latency: 1064.00 ms
- P95 latency: 1612.30 ms
- Max latency: 1631.00 ms

## Tokens And Cost
- Average total tokens: 256.94
- Total tokens: 4625.00
- Total cost: $0.005549
- Average cost per query: $0.000308

## Acceptance Status
- Overall status: PASS

| Metric | Actual | Threshold | Passed |
| --- | --- | --- | --- |
| intent_accuracy | 94.4% | 90.0% | yes |
| persona_accuracy | 88.9% | 85.0% | yes |
| joint_accuracy | 83.3% | 80.0% | yes |
| route_tier_accuracy | 100.0% | 90.0% | yes |
| short_circuit_precision | 100.0% | 95.0% | yes |

## Route Tier Distribution
- agentic: 14
- short_circuit: 2
- standard_search: 2

## Confidence Bands
- 0.85-1.00: count=10, intent_accuracy=100.0%, route_tier_accuracy=100.0%
- 0.65-0.84: count=7, intent_accuracy=85.7%, route_tier_accuracy=100.0%
- 0.40-0.64: count=1, intent_accuracy=100.0%, route_tier_accuracy=100.0%
- <0.40: count=0, intent_accuracy=0.0%, route_tier_accuracy=0.0%

## Operating Counts
- Proceed high-confidence: 10
- Proceed medium-confidence: 7
- Escalate low-confidence: 1
- Fallback insufficient-confidence: 0
- Fallback unknown-intent: 0

## Routing Health
- Route-mapping fallback threshold: 0.40
- Unknown predicted intent count: 0
- Unknown predicted intents: none

## Recommendations
- Intent accuracy meets the 90% baseline. Keep the current schema unless repeated confusion pairs remain operationally costly.
- Review persona slices with weak accuracy: advisor, parent.

## Worst-Performing Personas
| Persona | Count | Accuracy |
| --- | --- | --- |
| parent | 2 | 50.0% |
| advisor | 3 | 66.7% |
| high_school_student | 6 | 100.0% |
| counselor_teacher | 3 | 100.0% |
| college_b2b | 2 | 100.0% |

## Worst-Performing Intents
| Intent | Count | Accuracy |
| --- | --- | --- |
| rewrite_needed | 1 | 0.0% |
| comparison | 3 | 100.0% |
| b2b_partnership | 2 | 100.0% |
| filtered_search | 2 | 100.0% |
| multi_constraint | 2 | 100.0% |
| recommendation | 2 | 100.0% |
| admissions_process | 1 | 100.0% |
| attribute_lookup | 1 | 100.0% |

## Top Persona Confusions
| Gold Persona | Predicted Persona | Count | Row Rate |
| --- | --- | --- | --- |
| parent | counselor_teacher | 1 | 50.0% |
| advisor | college_student | 1 | 33.3% |

## Top Intent Confusions
| Gold Intent | Predicted Intent | Count | Row Rate |
| --- | --- | --- | --- |
| rewrite_needed | multi_constraint | 1 | 100.0% |

## Persona Confusion Matrix
| Gold \ Predicted | advisor | college_b2b | college_student | counselor_teacher | high_school_student | parent |
| --- | --- | --- | --- | --- | --- | --- |
| advisor | 2 | 0 | 1 | 0 | 0 | 0 |
| college_b2b | 0 | 2 | 0 | 0 | 0 | 0 |
| college_student | 0 | 0 | 2 | 0 | 0 | 0 |
| counselor_teacher | 0 | 0 | 0 | 3 | 0 | 0 |
| high_school_student | 0 | 0 | 0 | 0 | 6 | 0 |
| parent | 0 | 0 | 0 | 1 | 0 | 1 |

## Intent Confusion Matrix
| Gold \ Predicted | admissions_process | attribute_lookup | b2b_partnership | campus_life_fit | career_outcomes | comparison | cost_financial_aid | exact_lookup | filtered_search | multi_constraint | recommendation | rewrite_needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admissions_process | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| attribute_lookup | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| b2b_partnership | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| campus_life_fit | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| career_outcomes | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| comparison | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| cost_financial_aid | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| exact_lookup | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| filtered_search | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| multi_constraint | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| recommendation | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| rewrite_needed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |

## Route Tier Confusion Matrix
| Gold \ Predicted | agentic | short_circuit | standard_search |
| --- | --- | --- | --- |
| agentic | 14 | 0 | 0 |
| short_circuit | 0 | 2 | 0 |
| standard_search | 0 | 0 | 2 |

## Highest Confidence Wrong Predictions
- step3_0018: confidence=0.796, query=rewrite my why college essay opening
- step3_0010: confidence=0.764, query=what are FAFSA deadlines
- step3_0016: confidence=0.582, query=recommend colleges with exploratory studies programs for undecided students

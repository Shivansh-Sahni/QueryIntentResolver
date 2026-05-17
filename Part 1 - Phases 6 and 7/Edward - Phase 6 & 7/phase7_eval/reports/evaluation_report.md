# Phase 7 Evaluation Report

## Dataset Coverage
- Labels: 300
- Matched predictions: 300
- Missing predictions: 0

## Core Metrics
- Route accuracy: 88.7%
- Correct short-circuit rate: 95.1%
- Short-circuit precision: 88.6%
- Short-circuit boolean accuracy: 97.7%

## Latency
- Average latency: 1,042.74 ms
- P50 latency: 1,059.00 ms
- P95 latency: 1,791.20 ms
- Max latency: 1,899.00 ms

## Tokens And Cost
- Average total tokens: 304.00
- Total tokens: 91,199.00
- Total cost: $0.1092
- Average cost per query: $0.000364

## Route Accuracy By Gold Route
| Route | Count | Accuracy |
| --- | ---: | ---: |
| academic_advising | 2 | 50.0% |
| academic_policy_info | 7 | 71.4% |
| academic_program_info | 124 | 86.3% |
| campus_services_info | 126 | 95.2% |
| college_search | 34 | 76.5% |
| financial_aid_advising | 3 | 100.0% |
| housing_advising | 2 | 100.0% |
| study_abroad_advising | 1 | 100.0% |
| transfer_advising | 1 | 100.0% |

## Routing Path Distribution
| Routing Path | Count |
| --- | ---: |
| llm:academic_advising | 5 |
| llm:academic_policy_info | 7 |
| llm:academic_program_info | 107 |
| llm:campus_services_info | 83 |
| llm:college_search | 33 |
| llm:financial_aid_advising | 8 |
| llm:housing_advising | 6 |
| llm:study_abroad_advising | 3 |
| llm:transfer_advising | 4 |
| short_circuit | 44 |

## Confusion Matrix
| Gold \ Predicted | academic_advising | academic_policy_info | academic_program_info | campus_services_info | college_search | financial_aid_advising | housing_advising | study_abroad_advising | transfer_advising |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| academic_advising | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| academic_policy_info | 1 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| academic_program_info | 2 | 2 | 107 | 2 | 5 | 3 | 2 | 0 | 1 |
| campus_services_info | 0 | 0 | 0 | 120 | 1 | 3 | 0 | 1 | 1 |
| college_search | 1 | 0 | 0 | 3 | 26 | 0 | 2 | 1 | 1 |
| financial_aid_advising | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| housing_advising | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| study_abroad_advising | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| transfer_advising | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

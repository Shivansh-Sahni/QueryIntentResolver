# Dataset Initial vs Final Report

## Scope
This report compares the initial raw multi-file dataset to the final standardized training dataset used for the raw-eval experiment.

## Files Included
- `Data - Anika.csv`: 960 raw rows
- `Data - Edward.csv`: 2230 raw rows
- `Data - Nimisha.csv`: 1110 raw rows
- `Data - Ridhi.csv`: 1268 raw rows
- `Data - Shivansh.csv`: 4500 raw rows
- `Data Anthony.csv`: 1508 raw rows

## Initial Raw Dataset
- Total raw rows: 11576
- Unique `(Query, Persona, Intent)` triples before standardization: 9239
- Exact duplicate rows: 2001
- Duplicate `(Query, Persona, Intent)` rows: 2337
- Header-like junk rows: 1
- Raw persona label count: 31
- Raw intent label count: 31
- Raw route label count: 60

### Raw Persona Labels
- `advisor`
- `career_changer`
- `college`
- `college_admissions_officer`
- `college_b2b`
- `college_student`
- `colleges_b2b`
- `community_college_advisor`
- `community_college_student`
- `counselor`
- `counselor_teacher`
- `district_advisor`
- `edtech_founder`
- `employer`
- `employer_recruiter`
- `government_workforce_analyst`
- `graduate_applicant`
- `high_school_student`
- `highschool_student`
- `independent_counselor`
- `industry_hiring_manager`
- `international_student`
- `nonprofit_advisor`
- `parent`
- `persona`
- `rural_teacher`
- `scholarship_foundation_officer`
- `school_counselor`
- `teacher`
- `transfer_student`
- `urban_teacher`

### Raw Intent Labels
- `admissions_process`
- `advisory`
- `ambiguous`
- `analytics_request`
- `attribute_lookup`
- `b2b_partnership`
- `campus_life_fit`
- `career_outcomes`
- `comparison`
- `contextual_followup`
- `cost_financial_aid`
- `emotional_advisory`
- `exact_lookup`
- `factual`
- `filter_search`
- `filtered_search`
- `forecast`
- `guidance`
- `intent`
- `multi_constraint`
- `pathway`
- `policy_lookup`
- `pricing`
- `profile_management`
- `recommendation`
- `reflective_advisory`
- `rewrite_needed`
- `strategy`
- `support_request`
- `technical`
- `tool_request`

### Raw Route Labels
- `academic_advising`
- `academic_life_info`
- `academic_planning_advising`
- `academic_policy_info`
- `academic_program_info`
- `admissions_info`
- `agentic`
- `analytics`
- `analytics_filter`
- `analytics_route`
- `application_advising`
- `b2b_portal`
- `campus_services_info`
- `career_advising`
- `career_services_info`
- `college_prep_info`
- `college_search`
- `college_selection_advising`
- `compare_majors`
- `comparison_engine`
- `counselor_professional_dev`
- `counselor_resources`
- `counselor_student_advising`
- `counselor_tools`
- `course_selection_advising`
- `credit_transfer`
- `degree_planning`
- `filter_search`
- `filtered_search`
- `financial_aid_advising`
- `financial_aid_info`
- `grad_school_advising`
- `housing_advising`
- `llm`
- `llm_advisory`
- `llm_recommendation`
- `llm_strategy`
- `major_change_advising`
- `major_selection_advising`
- `metric_lookup`
- `nan`
- `opportunity_search`
- `parent_college_advising`
- `pathway_search`
- `platform_pricing`
- `platform_support`
- `policy_lookup`
- `route`
- `sales_pipeline`
- `search`
- `short_circuit`
- `simple_entity_info`
- `student_finance_advising`
- `student_life_advising`
- `student_wellbeing_advising`
- `study_abroad_advising`
- `test_prep_advising`
- `transfer_advising`
- `typesense_only`
- `undergraduate_research_advising`

## Final Standardized Training Dataset
- Accepted rows before dedup: 9157
- Final accepted rows after dedup: 6937
- Rows rejected: 2419
- Duplicate rows removed during final dedup: 2220
- Final canonical personas: advisor, college_b2b, college_student, counselor_teacher, high_school_student, parent
- Final canonical intents: admissions_process, attribute_lookup, b2b_partnership, campus_life_fit, career_outcomes, comparison, cost_financial_aid, direct_lookup, filtered_search, multi_constraint, recommendation, rewrite_needed

### Source Contribution Before Dedup
- `Data - Anika.csv`: 730 accepted, 230 rejected out of 960 raw rows
- `Data - Edward.csv`: 1918 accepted, 312 rejected out of 2230 raw rows
- `Data - Nimisha.csv`: 336 accepted, 774 rejected out of 1110 raw rows
- `Data - Ridhi.csv`: 543 accepted, 725 rejected out of 1268 raw rows
- `Data - Shivansh.csv`: 4464 accepted, 36 rejected out of 4500 raw rows
- `Data Anthony.csv`: 1166 accepted, 342 rejected out of 1508 raw rows

### Source Contribution After Dedup
- `Data - Shivansh.csv`: 2880 rows (41.52%)
- `Data - Edward.csv`: 1298 rows (18.71%)
- `Data Anthony.csv`: 1153 rows (16.62%)
- `Data - Anika.csv`: 730 rows (10.52%)
- `Data - Ridhi.csv`: 542 rows (7.81%)
- `Data - Nimisha.csv`: 334 rows (4.81%)

### Final Intent Distribution
- `filtered_search`: 2326 rows (33.53%)
- `attribute_lookup`: 1159 rows (16.71%)
- `multi_constraint`: 632 rows (9.11%)
- `cost_financial_aid`: 416 rows (6.00%)
- `admissions_process`: 384 rows (5.54%)
- `comparison`: 363 rows (5.23%)
- `b2b_partnership`: 347 rows (5.00%)
- `direct_lookup`: 339 rows (4.89%)
- `recommendation`: 299 rows (4.31%)
- `career_outcomes`: 281 rows (4.05%)
- `campus_life_fit`: 241 rows (3.47%)
- `rewrite_needed`: 150 rows (2.16%)

### Final Persona Distribution
- `high_school_student`: 1866 rows (26.90%)
- `parent`: 1137 rows (16.39%)
- `advisor`: 1099 rows (15.84%)
- `college_student`: 1070 rows (15.42%)
- `counselor_teacher`: 1035 rows (14.92%)
- `college_b2b`: 730 rows (10.52%)

### Rejection Breakdown
- `intent:unmapped`: 2038 rows (84.25%)
- `persona:unmapped`: 198 rows (8.19%)
- `intent:comparison_rejected_non_school`: 105 rows (4.34%)
- `intent:direct_lookup_rejected_not_entity_like`: 77 rows (3.18%)
- `query:blank_or_header`: 1 rows (0.04%)

## What Changed From Initial to Final
- Row count moved from 11,576 raw rows to 6,937 final standardized training rows.
- Label space moved from 31 raw persona labels to 6 final personas.
- Label space moved from 31 raw intent labels to 12 final intents.
- Route vocabulary moved from 60 raw route labels to deterministic routes derived from the 12 final intents.
- Obvious synonyms were standardized, for example `exact_lookup -> direct_lookup`, `filter_search -> filtered_search`, `highschool student -> high_school_student`, and counselor/teacher variants into `counselor_teacher`.
- Out-of-scope or weakly mappable rows were rejected instead of being force-fit into the schema.
- Testing stayed on untouched gold eval data; only training was standardized.

## Raw-Eval Training Result
- Persona accuracy: 0.533
- Intent accuracy: 0.423
- Route accuracy: 0.423
- Tier accuracy: 0.577
- Easy-path precision: 0.362
- Avg intent confidence: 0.599

### Model Comparison
- `nb`: persona 0.423, intent 0.380, route 0.380, tier 0.523
- `lsa_logreg`: persona 0.597, intent 0.403, route 0.403, tier 0.580
- `char_word_logreg`: persona 0.533, intent 0.423, route 0.423, tier 0.577

## Artifact Paths
- Standardized training dataset: `outputs_newdata_raw_eval_final/standardized_training_dataset.csv`
- Rejected rows audit: `outputs_newdata_raw_eval_final/rejected_training_rows.csv`
- Standardization summary: `outputs_newdata_raw_eval_final/training_standardization_summary.json`
- Metrics: `outputs_newdata_raw_eval_final/metrics.json`
- Predictions: `outputs_newdata_raw_eval_final/evaluation_predictions.csv`

Model Card - Final Complexity Classifier
========================================

Purpose
-------
Classify a user query into one of four handling complexity levels:
- `short_circuit`
- `medium`
- `complex`
- `llm_needed`


Inputs
------
- Query text only


Training choices
----------------
- Data source: six raw CSVs from `../Data/`
- Inconsistent label handling: dropped `high`
- Evaluation: grouped by normalized query text


Model
-----
- word TF-IDF
- char TF-IDF
- lightweight query-shape features
- `LinearSVC`


Best grouped-query result
-------------------------
- Accuracy: `0.816829`
- Avg confidence proxy: `0.599674`


Class performance
-----------------
- `complex`: precision `0.93`, recall `0.70`, f1 `0.80`
- `llm_needed`: precision `0.77`, recall `0.69`, f1 `0.73`
- `medium`: precision `0.81`, recall `0.90`, f1 `0.85`
- `short_circuit`: precision `0.73`, recall `0.80`, f1 `0.76`


Caveat
------
The dataset contains exact duplicate queries with conflicting labels. See:
- `label_ambiguity_summary.json`
- `top_ambiguous_queries.csv`

This means some remaining error is caused by annotation disagreement rather than
pure model failure.

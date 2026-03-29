Final Results
=============

Final objective
---------------
Predict the handling complexity of a query using only the raw query text.

Classes:
- `short_circuit`
- `medium`
- `complex`
- `llm_needed`


Chosen model
------------
- Training data: six raw CSVs in `Data/`
- Label cleanup: drop the inconsistent `high` label
- Split strategy: grouped by normalized query text
- Features:
  - word TF-IDF
  - char TF-IDF
  - lightweight query-pattern features
- Model: `LinearSVC`


Best strict result
------------------
- Accuracy: `0.816829`
- Output bundle: `final_outputs_complexity/`

Class-level report:
- `complex`: precision `0.93`, recall `0.70`, f1 `0.80`
- `llm_needed`: precision `0.77`, recall `0.69`, f1 `0.73`
- `medium`: precision `0.81`, recall `0.90`, f1 `0.85`
- `short_circuit`: precision `0.73`, recall `0.80`, f1 `0.76`


What improved
-------------
The final model outperformed the earlier strict grouped baseline by combining
text features with a small amount of explicit query-structure signal. The best
version stayed query-only; persona did not materially improve the strict setup.

Neural-network-style runs were tested through dense SVD + MLP pipelines, but
they did not beat the final linear SVM approach.


Main limitation
---------------
The raw labels contain non-trivial disagreement:
- `164` exact query strings have multiple complexity labels
- those queries account for `1,365` rows
- that is about `12.1%` of the dataset used in the final run

So the ceiling is partly limited by annotation inconsistency, not just by model
capacity.


Use this package
----------------
Use `train_complexity_primary.py` as the main script and `final_outputs_complexity/`
as the final artifact bundle.

Treat everything in `archive_legacy/` as historical context only.

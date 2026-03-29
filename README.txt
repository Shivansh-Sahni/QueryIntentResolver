Query Complexity Resolver - Final Workspace

What this folder now represents
--------------------------------
This workspace has been cleaned to reflect the final direction of the project:

- Primary task: predict query `Complexity`
- Target classes:
  - `short_circuit`
  - `medium`
  - `complex`
  - `llm_needed`
- Main input used for modeling: `Query` text only
- Persona and abstract intent are no longer treated as the main objective

The final recommendation is to route the project around complexity-first prediction,
because that is much closer to the real operational question:
"What level of handling does this query need?"


Top-level structure
-------------------
1. Data/
   The six raw source CSV files used for the final complexity-first work

2. train_complexity_primary.py
   Main training/evaluation script for the final complexity classifier

3. final_outputs_complexity/
   Final saved model, metrics, predictions, and label-noise audit for the
   best grouped-query run

4. FINAL_RESULTS.md
   Short final writeup describing the chosen setup, metrics, and limitations

5. requirements.txt
   Python dependencies for reproducing the final run

6. archive_legacy/
   Older intent-first, persona-first, route-first, and intermediate experiment
   artifacts kept only for traceability


Final model
-----------
Chosen setup:
- Training source: the six raw CSVs in `Data/`
- Label handling: keep the four real complexity labels and drop the inconsistent
  extra label `high`
- Evaluation split: grouped by normalized query text so repeated queries do not
  leak across train/test
- Features:
  - word TF-IDF
  - character TF-IDF
  - lightweight query-shape features
- Classifier: `LinearSVC`

This was the best honest result after trying:
- Naive Bayes
- Logistic regression
- SGD / linear models
- calibrated SVM variants
- MLP / neural-network-style baselines on dense SVD features

The neural-network runs did not beat the final linear SVM setup.


Final result to use
-------------------
The final artifact bundle is `final_outputs_complexity/`.

Most important files:
- `final_outputs_complexity/summary.txt`
- `final_outputs_complexity/best_grouped_metadata.json`
- `final_outputs_complexity/best_grouped_report.txt`
- `final_outputs_complexity/grouped_best_predictions.csv`
- `final_outputs_complexity/label_ambiguity_summary.json`
- `final_outputs_complexity/top_ambiguous_queries.csv`

Best strict grouped-query accuracy:
- `0.816829`

Why this is the right headline number:
- It evaluates on unseen query strings
- It avoids duplicate-query leakage
- It matches the real deployment problem better than random row splits


Important limitation
--------------------
The remaining bottleneck is not just model quality; it is label inconsistency in
the raw data.

From the final audit:
- rows used: `11,267`
- unique queries: `7,930`
- ambiguous exact queries: `164`
- ambiguous-query rows: `1,365`
- ambiguous-row share: about `12.1%`

That means some exact same query strings were labeled with different complexity
classes by different annotators. This is the main reason the system is not near
perfect even after stronger modeling.


How to reproduce
----------------
1. Install dependencies:
   pip install -r requirements.txt

2. Run the final complexity sweep:
   python train_complexity_primary.py --base_dir . --out_dir outputs_complexity_primary_repro

3. For the final chosen result, compare against:
   - `final_outputs_complexity/summary.txt`
   - `final_outputs_complexity/best_grouped_report.txt`


Archive note
------------
Everything in `archive_legacy/` is preserved intentionally, but it is not the
current recommendation. Those materials reflect earlier project framings
including intent-first, persona-first, route-first, and intermediate complexity
experiments.

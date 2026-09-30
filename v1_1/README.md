# Query Intent Resolver V1.1

A query-only routing component with auditable review integration, grouped model selection, separately reported applicability testing and a tested API. The old `v1/` release remains unchanged.

## Start here

After a successful build, open:

- `docs/REVIEWER_BRIEF.html`: self-contained reviewer dashboard.
- `docs/EXECUTIVE_HANDOFF.pdf`: printable executive handoff.
- `docs/TECHNICAL_CLOSEOUT.md`: complete methodology, metrics and limitations.
- `artifacts/SUMMARY.json`: exact executed results.
- `artifacts/COMPLETION_MATRIX.json`: engineering vs quality vs deployment status.
- `artifacts/applicability/core/errors.csv`: unsuccessful core examples.

**Engineering completion is not production authorization.** A green build proves reproducibility and interfaces, not acceptable real-user routing accuracy. The model-quality gates remain fixed, and live route bindings and independent real-query validation remain external requirements.

## Reproduce

From the repository root, using Python 3.11:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r v1_1/requirements.txt
python v1_1/scripts/materialize_frozen_suite.py
PYTHONPATH=v1_1 pytest -q v1_1/tests
PYTHONPATH=v1_1 python -m qir_release.build --repo-root .
```

Windows PowerShell: activate `.venv\Scripts\Activate.ps1`, set `$env:PYTHONPATH="v1_1"`, then run the same Python/pytest commands without the inline `PYTHONPATH=` prefix.

This rebuilds `v1_1/artifacts/`, never the old `v1/artifacts/`. Review integration preserves the original submission. Template-family exclusions and model selection are recorded. The protocol and applicability suite must not be changed after evaluation without a new, disclosed experiment.

## Run the API

```bash
PYTHONPATH=v1_1 uvicorn qir_release.api:app --host 127.0.0.1 --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/v1/resolve \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"UCLA vs USC for engineering"}'
```

Success returns exactly `route` and `confidence`. Illustrative shape:

```json
{"route":"complex","confidence":0.91}
```

`route` is one of `short_circuit`, `medium`, `complex`, `llm_needed`. Optional `persona`, `page`, `filters`, `context`, `session` are accepted but ignored for prediction. No downstream service is invoked. `GET /ready` reports model availability, not production approval. The batch endpoint accepts at most 100 requests.

CLI:

```bash
PYTHONPATH=v1_1 python -m qir_release "colleges in California"
```

Set `QIR_BUNDLE` to a trusted release directory. Set `QIR_API_KEY` for shared environments and send it as `X-API-Key`. Do not publicly expose an unauthenticated development server. TLS, access control and rate limiting belong at the approved gateway. The runtime never logs raw queries.

## What changed

The submitted 55-row peer review is structurally checked against the original quarantine queue. Equivalent template disagreements are resolved in an explicitly attributed AI-assisted policy pass; the original review is not overwritten. Context-dependent cases remain excluded. The exact numbers accepted, adjudicated, deferred and retained in the strict fit are reported by the build.

The model sweep includes fixed Logistic Regression, LinearSVC and SGD candidates. Three-fold grouped OOF selection encloses grouped calibration of the entire text feature pipeline. A lookup rule is enabled only if the preregistered training evidence requirements are met. The final model and routing policy are saved before evaluation labels are read.

The original balanced 300-query benchmark is preserved as historical regression evidence, not presented as a new blind test. A 100-case core applicability set and 20-case boundary set are separately reported, including failures and training overlaps. These are assistant-authored tests, not a fabricated independent teammate submission or real traffic sample.

## Layout

```text
config/       fixed protocol and unbound deployment examples
data/         original submitted review and frozen diagnostic tests
qir_release/  review import, modeling, metrics, API, integration and reports
tests/        unit and contract regressions
artifacts/    generated data, OOF selection, comparisons and verification
docs/         reviewer brief, detailed report and integration documentation
```

The model artifact is a trusted Python joblib bundle, not a safe general file format. Hash verification detects accidental alteration but does not authenticate an attacker-provided pickle. Only load artifacts built from trusted reviewed repository code.

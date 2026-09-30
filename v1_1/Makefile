# From repository root: make -f v1_1/Makefile <target>
.PHONY: test build serve

test:
	python v1_1/scripts/materialize_frozen_suite.py
	PYTHONPATH=v1_1 python -m pytest -q v1_1/tests
build:
	python v1_1/scripts/materialize_frozen_suite.py
	PYTHONPATH=v1_1 python -m qir_release.build --repo-root .
	python v1_1/scripts/finalize_presentation.py
serve:
	PYTHONPATH=v1_1 uvicorn qir_release.api:app --host 127.0.0.1 --port 8000

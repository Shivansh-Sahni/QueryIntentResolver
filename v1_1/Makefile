# Invoke from repository root: make -f v1_1/Makefile <target>
.PHONY: test build serve

test:
	PYTHONPATH=v1_1 python -m pytest -q v1_1/tests
build:
	PYTHONPATH=v1_1 python -m qir_release.build --repo-root .
serve:
	PYTHONPATH=v1_1 uvicorn qir_release.api:app --host 127.0.0.1 --port 8000

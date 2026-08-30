.PHONY: install install-zero-shot test build build-zero-shot api validate zero-shot rules compare package

install:
	python -m pip install -r requirements.txt

install-zero-shot:
	python -m pip install -r requirements-zero-shot.txt

test:
	PYTHONPATH=src pytest -q tests

build:
	cd .. && PYTHONPATH=v1/src python v1/scripts/run_v1_pipeline.py --benchmark-size 300

build-zero-shot:
	cd .. && PYTHONPATH=v1/src python v1/scripts/run_v1_pipeline.py --benchmark-size 300 --with-zero-shot

api:
	cd .. && PYTHONPATH=v1/src uvicorn qir_v1.api:app --host 0.0.0.0 --port 8000

validate:
	cd .. && PYTHONPATH=v1/src python v1/scripts/validate_v1_artifacts.py --artifacts-dir v1/artifacts

rules:
	cd .. && PYTHONPATH=v1/src python v1/scripts/run_rules_baseline.py \
		--benchmark v1/artifacts/benchmark/benchmark_gold.csv \
		--output-dir v1/artifacts/models/rules \
		--policy v1/config/route_policy.json

zero-shot:
	cd .. && PYTHONPATH=v1/src python v1/scripts/run_zero_shot_baseline.py \
		--benchmark v1/artifacts/benchmark/benchmark_gold.csv \
		--output-dir v1/artifacts/models/zero_shot \
		--policy v1/config/route_policy.json

compare:
	cd .. && PYTHONPATH=v1/src python v1/scripts/compare_models.py \
		--metrics-root v1/artifacts/models \
		--output-dir v1/artifacts/shootout \
		--benchmark-manifest v1/artifacts/benchmark/benchmark_manifest.json \
		--policy v1/config/route_policy.json

package:
	cd .. && tar -czf qir-v1-complete.tar.gz v1

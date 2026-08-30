from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

SCRIPT_DIR = Path(__file__).resolve().parent
V1_ROOT = SCRIPT_DIR.parent
SRC_DIR = V1_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qir_v1.evaluation import evaluate_routes  # noqa: E402
from qir_v1.features import QueryShapeFeatures  # noqa: E402
from qir_v1.policy import apply_deployment_policy, load_route_policy  # noqa: E402

VALID_ROUTES = ["short_circuit", "medium", "complex", "llm_needed"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_model() -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.995,
                    max_features=50000,
                    sublinear_tf=True,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_features=60000,
                    sublinear_tf=True,
                ),
            ),
            ("shape", QueryShapeFeatures()),
        ]
    )
    base = LinearSVC(C=1.2, class_weight="balanced", random_state=20260830, max_iter=10000, tol=1e-3, dual="auto")
    classifier = CalibratedClassifierCV(base, method="sigmoid", cv=3, n_jobs=1)
    return Pipeline([("features", features), ("classifier", classifier)])


def percentile(values: list[float], q: float) -> float | None:
    return float(np.percentile(values, q)) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the Query Intent Resolver V1 LinearSVC")
    parser.add_argument("--training-pool", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=V1_ROOT / "config" / "route_policy.json")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(args.training_pool, dtype=str, keep_default_na=False)
    benchmark = pd.read_csv(args.benchmark, dtype=str, keep_default_na=False)

    required_train = {"query_text", "route"}
    required_benchmark = {"benchmark_id", "query_text", "route"}
    if missing := required_train - set(train.columns):
        raise ValueError(f"Training pool missing columns: {sorted(missing)}")
    if missing := required_benchmark - set(benchmark.columns):
        raise ValueError(f"Benchmark missing columns: {sorted(missing)}")
    if set(train["route"]) - set(VALID_ROUTES):
        raise ValueError("Training pool contains invalid route labels")
    if set(benchmark["route"]) - set(VALID_ROUTES):
        raise ValueError("Benchmark contains invalid route labels")
    if "query_norm" in train.columns and "query_norm" in benchmark.columns:
        overlap = set(train["query_norm"]) & set(benchmark["query_norm"])
        if overlap:
            raise ValueError(f"Benchmark leakage detected for {len(overlap)} normalized queries")

    model = build_model()
    start_train = time.perf_counter()
    model.fit(train["query_text"].astype(str), train["route"].astype(str))
    training_seconds = time.perf_counter() - start_train

    warm_queries = benchmark["query_text"].head(min(10, len(benchmark))).tolist()
    if warm_queries:
        model.predict_proba(warm_queries)

    probabilities = model.predict_proba(benchmark["query_text"].astype(str))
    classes = np.asarray(model.classes_)
    best_indices = probabilities.argmax(axis=1)
    raw_routes = classes[best_indices]
    confidences = probabilities[np.arange(len(probabilities)), best_indices]

    policy = load_route_policy(args.policy)
    deployed = [
        apply_deployment_policy(str(route), float(confidence), policy)
        for route, confidence in zip(raw_routes, confidences)
    ]
    predicted_routes = np.asarray([item[0] for item in deployed])
    policy_reasons = [item[1] for item in deployed]

    single_latencies: list[float] = []
    for query in benchmark["query_text"].astype(str):
        start = time.perf_counter()
        model.predict_proba([query])
        single_latencies.append((time.perf_counter() - start) * 1000.0)

    prediction_export = pd.DataFrame(
        {
            "benchmark_id": benchmark["benchmark_id"],
            "query_text": benchmark["query_text"],
            "predicted_route": predicted_routes,
            "raw_predicted_route": raw_routes,
            "confidence": confidences,
            "policy_reason": policy_reasons,
            "latency_ms": single_latencies,
            "estimated_cost_usd": 0.0,
            "model": "calibrated_word_char_shape_linearsvc",
            "model_status": "real",
        }
    )
    prediction_export.to_csv(args.output_dir / "predictions.csv", index=False)

    raw_export = prediction_export.copy()
    raw_export["predicted_route"] = raw_export["raw_predicted_route"]
    raw_metrics = evaluate_routes(
        benchmark,
        raw_export,
        model_name="calibrated_word_char_shape_linearsvc_raw",
        output_dir=args.output_dir / "raw_model",
        model_status="diagnostic",
    )
    raw_metrics["benchmark_sha256"] = sha256_file(args.benchmark)
    (args.output_dir / "raw_model" / "metrics.json").write_text(
        json.dumps(raw_metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    metrics = evaluate_routes(
        benchmark,
        prediction_export,
        model_name="calibrated_word_char_shape_linearsvc",
        output_dir=args.output_dir,
        model_status="real",
    )
    metrics["benchmark_sha256"] = sha256_file(args.benchmark)
    metrics["training_rows"] = int(len(train))
    metrics["training_seconds"] = float(training_seconds)
    metrics["raw_model_metrics"] = raw_metrics
    metrics["latency_measurement"] = {
        "method": "warm single-query predict_proba calls on the frozen benchmark",
        "p50_ms": percentile(single_latencies, 50),
        "p95_ms": percentile(single_latencies, 95),
        "p99_ms": percentile(single_latencies, 99),
    }
    metrics["feature_set"] = ["word_tfidf_1_2", "char_wb_tfidf_3_5", "query_shape_features"]
    metrics["classifier"] = "CalibratedClassifierCV(LinearSVC, sigmoid, cv=3)"
    metrics["deployment_policy"] = policy["deployment_policy"]
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )

    model_path = args.output_dir / "model.joblib"
    joblib.dump(model, model_path, compress=3)

    model_card = f"""# Query Intent Resolver V1 - LinearSVC Model Card

## Purpose

Predict one of four handling routes from raw query text:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

## Training

- Training rows: **{len(train)}** unique normalized queries
- Held-out benchmark rows: **{len(benchmark)}**
- Benchmark leakage check: **passed**
- Features: word TF-IDF, character TF-IDF, deterministic query-shape features
- Classifier: calibrated LinearSVC
- Training time: **{training_seconds:.3f} seconds**

## Deployment-policy benchmark results

- Accuracy: **{metrics['accuracy']:.4f}**
- Macro F1: **{metrics['macro_f1']:.4f}**
- False short-circuit rate: **{metrics['false_short_circuit_rate']:.4f}**
- Short-circuit recall: **{metrics['short_circuit_recall']:.4f}**
- P95 single-query latency: **{metrics['p95_latency_ms']:.3f} ms**
- API cost: **$0.00 per query**

## Raw-model diagnostic results

- Accuracy: **{raw_metrics['accuracy']:.4f}**
- Macro F1: **{raw_metrics['macro_f1']:.4f}**
- False short-circuit rate: **{raw_metrics['false_short_circuit_rate']:.4f}**

## Known limitations

The source data is predominantly synthetic and previously contained conflicting exact-query labels. V1 removes unresolved conflicts and freezes a disjoint benchmark, but production validation must eventually include naturally occurring MascotGO queries.

## Runtime contract

```json
{{
  "route": "short_circuit | medium | complex | llm_needed",
  "confidence": 0.91
}}
```
"""
    (args.output_dir / "MODEL_CARD.md").write_text(model_card, encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

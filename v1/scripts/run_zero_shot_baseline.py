from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
V1_ROOT = SCRIPT_DIR.parent
SRC_DIR = V1_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qir_v1.evaluation import evaluate_routes  # noqa: E402
from qir_v1.policy import apply_deployment_policy, load_route_policy  # noqa: E402

LABEL_DESCRIPTIONS = {
    "short_circuit": "a deterministic exact entity or one-hop factual lookup with no language-model reasoning",
    "medium": "an ordinary factual search, process question, or one-to-two-filter retrieval task",
    "complex": "a comparison, ranking, recommendation, multi-constraint search, planning task, or multi-step workflow",
    "llm_needed": "a subjective, ambiguous, emotional, advisory, or semantic interpretation that needs a language model",
}
DESCRIPTION_TO_ROUTE = {description: route for route, description in LABEL_DESCRIPTIONS.items()}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local zero-shot language-model V1 baseline")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="typeform/distilbert-base-uncased-mnli")
    parser.add_argument("--policy", type=Path, default=V1_ROOT / "config" / "route_policy.json")
    parser.add_argument("--compute-hourly-usd", type=float, default=0.06)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    try:
        from transformers import pipeline
    except ImportError as exc:
        raise SystemExit("Install v1/requirements-zero-shot.txt before running this baseline") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    benchmark = pd.read_csv(args.benchmark, dtype=str, keep_default_na=False)
    required = {"benchmark_id", "query_text", "route"}
    if missing := required - set(benchmark.columns):
        raise ValueError(f"Benchmark is missing columns: {sorted(missing)}")

    classifier = pipeline("zero-shot-classification", model=args.model, device=-1, framework="pt")
    candidate_labels = list(DESCRIPTION_TO_ROUTE)
    policy = load_route_policy(args.policy)
    rows: list[dict[str, object]] = []

    total_started = time.perf_counter()
    for start in range(0, len(benchmark), args.batch_size):
        batch = benchmark.iloc[start : start + args.batch_size]
        batch_started = time.perf_counter()
        results = classifier(
            batch["query_text"].astype(str).tolist(),
            candidate_labels=candidate_labels,
            hypothesis_template="This college-related query requires {}.",
            multi_label=False,
            batch_size=args.batch_size,
        )
        batch_seconds = time.perf_counter() - batch_started
        if isinstance(results, dict):
            results = [results]
        per_query_latency_ms = batch_seconds * 1000.0 / max(len(batch), 1)

        for item, result in zip(batch.itertuples(index=False), results):
            description = str(result["labels"][0])
            raw_route = DESCRIPTION_TO_ROUTE[description]
            confidence = float(result["scores"][0])
            route, reason = apply_deployment_policy(raw_route, confidence, policy)
            rows.append(
                {
                    "benchmark_id": item.benchmark_id,
                    "query_text": item.query_text,
                    "predicted_route": route,
                    "raw_predicted_route": raw_route,
                    "confidence": confidence,
                    "policy_reason": reason,
                    "latency_ms": per_query_latency_ms,
                    "estimated_cost_usd": 0.0,
                    "model": f"zero_shot::{args.model}",
                    "model_status": "real",
                }
            )

    elapsed_seconds = time.perf_counter() - total_started
    compute_cost = elapsed_seconds / 3600.0 * args.compute_hourly_usd
    predictions = pd.DataFrame(rows)
    predictions["estimated_cost_usd"] = compute_cost / max(len(predictions), 1)
    predictions.to_csv(args.output_dir / "predictions.csv", index=False)

    metrics = evaluate_routes(
        benchmark,
        predictions,
        model_name=f"zero_shot::{args.model}",
        output_dir=args.output_dir,
        model_status="real",
    )
    metrics["benchmark_sha256"] = sha256_file(args.benchmark)
    metrics["total_inference_seconds"] = elapsed_seconds
    metrics["batch_size"] = args.batch_size
    metrics["compute_hourly_usd_assumption"] = args.compute_hourly_usd
    metrics["model_type"] = "local_zero_shot_nli_language_model_baseline"
    metrics["deployment_policy"] = policy["deployment_policy"]
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
V1_ROOT = SCRIPT_DIR.parent
SRC_DIR = V1_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qir_v1.evaluation import evaluate_routes  # noqa: E402
from qir_v1.policy import apply_deployment_policy, load_route_policy  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_prediction_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "predicted_route": ["predicted_route", "route", "routing_tier", "prediction"],
        "confidence": ["confidence", "predicted_confidence", "score"],
        "benchmark_id": ["benchmark_id", "benchmark_row_id", "row_id", "id"],
        "latency_ms": ["latency_ms", "inference_latency_ms", "latency"],
        "estimated_cost_usd": ["estimated_cost_usd", "cost_usd", "cost"],
    }
    lower = {str(column).strip().lower(): column for column in df.columns}
    rename: dict[str, str] = {}
    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in lower:
                rename[lower[candidate]] = target
                break
    result = df.rename(columns=rename).copy()
    if "confidence" not in result:
        result["confidence"] = 0.5
    if "latency_ms" not in result:
        result["latency_ms"] = pd.NA
    if "estimated_cost_usd" not in result:
        result["estimated_cost_usd"] = 0.0
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a model export against the frozen V1 benchmark")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-status", default="real", choices=["real", "diagnostic", "simulated", "pending"])
    parser.add_argument("--policy", type=Path, default=V1_ROOT / "config" / "route_policy.json")
    parser.add_argument("--skip-deployment-policy", action="store_true")
    args = parser.parse_args()

    gold = pd.read_csv(args.benchmark, dtype=str, keep_default_na=False)
    predictions = normalize_prediction_columns(
        pd.read_csv(args.predictions, dtype=str, keep_default_na=False)
    )
    required = {"benchmark_id", "predicted_route", "confidence"}
    if missing := required - set(predictions.columns):
        raise ValueError(f"Predictions are missing columns: {sorted(missing)}")

    predictions["confidence"] = pd.to_numeric(
        predictions["confidence"], errors="coerce"
    ).fillna(0.5).clip(0.0, 1.0)
    predictions["raw_predicted_route"] = predictions["predicted_route"].astype(str).str.strip().str.lower()

    if not args.skip_deployment_policy:
        policy = load_route_policy(args.policy)
        adjusted = [
            apply_deployment_policy(route, float(confidence), policy)
            for route, confidence in zip(
                predictions["raw_predicted_route"], predictions["confidence"]
            )
        ]
        predictions["predicted_route"] = [item[0] for item in adjusted]
        predictions["policy_reason"] = [item[1] for item in adjusted]
    else:
        predictions["predicted_route"] = predictions["raw_predicted_route"]
        predictions["policy_reason"] = "deployment_policy_skipped"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "predictions.csv", index=False)
    metrics = evaluate_routes(
        gold,
        predictions,
        model_name=args.model_name,
        output_dir=args.output_dir,
        model_status=args.model_status,
    )
    metrics["benchmark_sha256"] = sha256_file(args.benchmark)
    metrics["deployment_policy_applied"] = not args.skip_deployment_policy
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

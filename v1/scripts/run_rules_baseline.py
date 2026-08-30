from __future__ import annotations

import argparse
import hashlib
import json
import re
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_rule(query: str) -> tuple[str, float, str]:
    text = " ".join(query.casefold().split())
    words = re.findall(r"[a-z0-9']+", text)

    if any(term in text for term in (" vs ", "compare ", "comparison", "better than")):
        return "complex", 0.90, "comparison"
    if any(term in text for term in ("recommend", "what schools should", "schools like", "best colleges", "best schools")):
        return "complex", 0.84, "recommendation_or_ranking"
    constraint_markers = sum(
        int(term in text)
        for term in (" under ", " with ", " near ", " but ", " and ", " not ", " cheaper", "affordable")
    )
    if constraint_markers >= 2:
        return "complex", 0.80, "multiple_constraints"
    if any(term in text for term in ("vibe", "fit", "stress", "normal people", "culture", "feel about", "worried", "anxious")):
        return "llm_needed", 0.82, "subjective_or_advisory"
    if any(text.startswith(prefix) for prefix in ("colleges ", "schools ", "universities ")):
        return "medium", 0.76, "category_or_filter_search"
    if len(words) <= 4 and any(
        term in text
        for term in (
            "tuition", "acceptance rate", "sat", "act", "deadline", "ranking", "housing", "location"
        )
    ):
        return "short_circuit", 0.83, "one_hop_attribute"
    if len(words) <= 4 and not any(char in text for char in "?!"):
        return "short_circuit", 0.81, "short_entity_like_query"
    return "medium", 0.72, "default_standard_search"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic diagnostic floor on the frozen V1 benchmark")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=V1_ROOT / "config" / "route_policy.json")
    args = parser.parse_args()

    benchmark = pd.read_csv(args.benchmark, dtype=str, keep_default_na=False)
    required = {"benchmark_id", "query_text", "route"}
    if missing := required - set(benchmark.columns):
        raise ValueError(f"Benchmark is missing columns: {sorted(missing)}")

    policy = load_route_policy(args.policy)
    rows: list[dict[str, object]] = []
    for item in benchmark.itertuples(index=False):
        started = time.perf_counter()
        raw_route, confidence, rule = raw_rule(item.query_text)
        route, policy_reason = apply_deployment_policy(raw_route, confidence, policy)
        latency_ms = (time.perf_counter() - started) * 1000.0
        rows.append(
            {
                "benchmark_id": item.benchmark_id,
                "query_text": item.query_text,
                "predicted_route": route,
                "raw_predicted_route": raw_route,
                "confidence": confidence,
                "rule": rule,
                "policy_reason": policy_reason,
                "latency_ms": latency_ms,
                "estimated_cost_usd": 0.0,
                "model": "deterministic_rules_v1",
                "model_status": "diagnostic",
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.DataFrame(rows)
    predictions.to_csv(args.output_dir / "predictions.csv", index=False)
    metrics = evaluate_routes(
        benchmark,
        predictions,
        model_name="deterministic_rules_v1",
        output_dir=args.output_dir,
        model_status="diagnostic",
    )
    metrics["benchmark_sha256"] = sha256_file(args.benchmark)
    metrics["model_type"] = "deterministic_diagnostic_floor"
    metrics["deployment_policy"] = policy["deployment_policy"]
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

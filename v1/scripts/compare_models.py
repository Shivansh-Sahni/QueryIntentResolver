from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_metrics(root: Path, benchmark_sha256: str, benchmark_rows: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(root.rglob("metrics.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        required = {"model_name", "accuracy", "macro_f1", "false_short_circuit_rate"}
        if not required.issubset(item):
            continue
        item["metrics_path"] = str(path)
        item["benchmark_verified"] = (
            item.get("benchmark_sha256") == benchmark_sha256
            and int(item.get("benchmark_rows", -1)) == benchmark_rows
        )
        results.append(item)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare real V1 models on the identical frozen benchmark")
    parser.add_argument("--metrics-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--benchmark-manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    guardrails = policy["winner_selection"]
    weights = guardrails["score_weights"]
    manifest = json.loads(args.benchmark_manifest.read_text(encoding="utf-8"))
    benchmark_sha256 = str(manifest["benchmark_gold_sha256"])
    benchmark_rows = int(manifest.get("benchmark_rows", manifest["benchmark_size"]))

    metrics = load_metrics(args.metrics_root, benchmark_sha256, benchmark_rows)
    if not metrics:
        raise ValueError(f"No compatible metrics.json files found below {args.metrics_root}")

    rows: list[dict[str, Any]] = []
    for item in metrics:
        accuracy = safe_float(item.get("accuracy"), 0.0)
        macro_f1 = safe_float(item.get("macro_f1"), 0.0)
        false_short = safe_float(item.get("false_short_circuit_rate"), 1.0)
        short_recall = safe_float(item.get("short_circuit_recall"), 0.0)
        p95 = safe_float(item.get("p95_latency_ms"), float("inf"))
        cost = safe_float(item.get("estimated_cost_per_1000_queries_usd"), float("inf"))
        coverage = safe_float(item.get("coverage"), 0.0)
        model_status = str(item.get("model_status", "real"))
        benchmark_verified = bool(item["benchmark_verified"])
        eligible = (
            model_status == "real"
            and benchmark_verified
            and coverage == 1.0
            and accuracy >= float(guardrails["min_accuracy"])
            and macro_f1 >= float(guardrails["min_macro_f1"])
            and short_recall >= float(guardrails["min_short_circuit_recall"])
            and false_short <= float(guardrails["max_false_short_circuit_rate"])
        )
        score = (
            float(weights["macro_f1"]) * macro_f1
            + float(weights["accuracy"]) * accuracy
            + float(weights["short_circuit_safety"]) * (1.0 - false_short)
            + float(weights["short_circuit_recall"]) * short_recall
        )
        rows.append(
            {
                "model_name": str(item["model_name"]),
                "model_status": model_status,
                "benchmark_verified": benchmark_verified,
                "eligible": eligible,
                "selection_score": score,
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "false_short_circuit_rate": false_short,
                "short_circuit_recall": short_recall,
                "p95_latency_ms": None if p95 == float("inf") else p95,
                "estimated_cost_per_1000_queries_usd": None if cost == float("inf") else cost,
                "coverage": coverage,
                "metrics_path": str(item["metrics_path"]),
            }
        )

    table = pd.DataFrame(rows)
    table["_p95"] = table["p95_latency_ms"].fillna(float("inf"))
    table["_cost"] = table["estimated_cost_per_1000_queries_usd"].fillna(float("inf"))
    table = table.sort_values(
        ["eligible", "selection_score", "false_short_circuit_rate", "macro_f1", "accuracy", "_cost", "_p95"],
        ascending=[False, False, True, False, False, True, True],
    ).drop(columns=["_p95", "_cost"]).reset_index(drop=True)
    table.insert(0, "rank", range(1, len(table) + 1))
    table.to_csv(args.output_dir / "shootout_summary.csv", index=False)

    eligible_table = table.loc[table["eligible"]]
    winner_row = (eligible_table.iloc[0] if len(eligible_table) else table.iloc[0]).to_dict()
    verified_real = table.loc[(table["model_status"] == "real") & table["benchmark_verified"]]
    minimum_models = int(guardrails["minimum_real_models_for_final"])
    status = "final" if len(verified_real) >= minimum_models and bool(winner_row["eligible"]) else "provisional"

    winner = {
        "schema_version": "1.0.0",
        "status": status,
        "winner": winner_row,
        "benchmark_sha256": benchmark_sha256,
        "benchmark_rows": benchmark_rows,
        "verified_real_models_evaluated": int(len(verified_real)),
        "selection_policy": guardrails,
        "finalization_rule": "Final only after the required number of real models are verified against the identical frozen benchmark.",
    }
    (args.output_dir / "winner.json").write_text(json.dumps(winner, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Query Intent Resolver V1 Model Shootout",
        "",
        f"- Status: **{status}**",
        f"- Current leader: **{winner_row['model_name']}**",
        f"- Verified real models: **{len(verified_real)}**",
        f"- Benchmark SHA-256: `{benchmark_sha256}`",
        "",
        "| Rank | Model | Status | Benchmark Verified | Eligible | Accuracy | Macro F1 | False SC | SC Recall | P95 ms | Cost / 1K |",
        "| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in table.to_dict(orient="records"):
        p95_text = "" if pd.isna(row["p95_latency_ms"]) else f"{float(row['p95_latency_ms']):.3f}"
        cost_text = "" if pd.isna(row["estimated_cost_per_1000_queries_usd"]) else f"${float(row['estimated_cost_per_1000_queries_usd']):.6f}"
        lines.append(
            f"| {int(row['rank'])} | `{row['model_name']}` | {row['model_status']} | {row['benchmark_verified']} | "
            f"{row['eligible']} | {float(row['accuracy']):.4f} | {float(row['macro_f1']):.4f} | "
            f"{float(row['false_short_circuit_rate']):.4f} | {float(row['short_circuit_recall']):.4f} | {p95_text} | {cost_text} |"
        )
    lines.extend([
        "",
        "## Decision order",
        "",
        "1. Identical frozen benchmark and complete coverage.",
        "2. Pass false-short-circuit and quality guardrails.",
        "3. Rank by the frozen safety-weighted score.",
        "4. Use latency and cost as tie-breakers among comparable models.",
        "",
        "Diagnostic entries are reported for transparency but cannot win.",
    ])
    (args.output_dir / "SHOOTOUT_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(winner, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

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

        base_real_requirements = (
            model_status == "real"
            and benchmark_verified
            and coverage == 1.0
            and accuracy >= float(guardrails["min_accuracy"])
            and macro_f1 >= float(guardrails["min_macro_f1"])
        )
        safety_candidate = (
            base_real_requirements
            and false_short <= float(guardrails["max_false_short_circuit_rate"])
        )
        eligible = (
            safety_candidate
            and short_recall >= float(guardrails["min_short_circuit_recall"])
        )

        if eligible:
            selection_tier = "eligible"
            tier_rank = 0
        elif safety_candidate:
            selection_tier = "provisional_safe"
            tier_rank = 1
        elif model_status == "real" and benchmark_verified and coverage == 1.0:
            selection_tier = "real_ineligible"
            tier_rank = 2
        elif model_status == "diagnostic":
            selection_tier = "diagnostic_only"
            tier_rank = 3
        else:
            selection_tier = "invalid_or_unverified"
            tier_rank = 4

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
                "safety_candidate": safety_candidate,
                "selection_tier": selection_tier,
                "_tier_rank": tier_rank,
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
        ["_tier_rank", "selection_score", "false_short_circuit_rate", "macro_f1", "accuracy", "_cost", "_p95"],
        ascending=[True, False, True, False, False, True, True],
    ).drop(columns=["_p95", "_cost"]).reset_index(drop=True)
    table.insert(0, "rank", range(1, len(table) + 1))

    output_table = table.drop(columns=["_tier_rank"])
    output_table.to_csv(args.output_dir / "shootout_summary.csv", index=False)

    score_leader = table.sort_values(
        ["selection_score", "false_short_circuit_rate", "macro_f1", "accuracy"],
        ascending=[False, True, False, False],
    ).iloc[0].drop(labels=["_tier_rank"]).to_dict()

    eligible_table = table.loc[table["eligible"]]
    safe_table = table.loc[table["safety_candidate"]]
    verified_real = table.loc[(table["model_status"] == "real") & table["benchmark_verified"] & (table["coverage"] == 1.0)]

    if len(eligible_table):
        selected_row = eligible_table.iloc[0]
        selection_basis = "all_release_guardrails_passed"
        provisional_reason = ""
    elif len(safe_table):
        selected_row = safe_table.iloc[0]
        selection_basis = "best_real_model_passing_quality_and_false_short_circuit_guardrails"
        provisional_reason = "No real model currently passes every release guardrail, including minimum short-circuit recall."
    elif len(verified_real):
        selected_row = verified_real.iloc[0]
        selection_basis = "best_verified_real_model_pending_safety_improvement"
        provisional_reason = "No verified real model currently passes the routing-safety guardrails."
    else:
        raise ValueError("No verified real model with complete benchmark coverage is available for recommendation")

    recommended_row = selected_row.drop(labels=["_tier_rank"]).to_dict()
    minimum_models = int(guardrails["minimum_real_models_for_final"])
    status = (
        "final"
        if len(verified_real) >= minimum_models and bool(recommended_row["eligible"])
        else "provisional"
    )

    winner = {
        "schema_version": "1.0.1",
        "status": status,
        "winner": recommended_row,
        "recommended_model": recommended_row,
        "leaderboard_leader": score_leader,
        "selection_basis": selection_basis,
        "provisional_reason": provisional_reason,
        "benchmark_sha256": benchmark_sha256,
        "benchmark_rows": benchmark_rows,
        "verified_real_models_evaluated": int(len(verified_real)),
        "selection_policy": guardrails,
        "finalization_rule": "Final only after enough verified real models are evaluated and the recommended model passes every frozen release guardrail.",
        "diagnostic_policy": "Diagnostic entries are reported for analysis but can never be the recommended or packaged model.",
    }
    (args.output_dir / "winner.json").write_text(json.dumps(winner, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Query Intent Resolver V1 Model Shootout",
        "",
        f"- Status: **{status}**",
        f"- Recommended model: **{recommended_row['model_name']}**",
        f"- Selection basis: **{selection_basis}**",
        f"- Highest raw score (analysis only): **{score_leader['model_name']}**",
        f"- Verified real models: **{len(verified_real)}**",
        f"- Benchmark SHA-256: `{benchmark_sha256}`",
    ]
    if provisional_reason:
        lines.append(f"- Why provisional: {provisional_reason}")
    lines.extend([
        "",
        "| Rank | Model | Tier | Status | Verified | Eligible | Safety candidate | Accuracy | Macro F1 | False SC | SC Recall | P95 ms | Cost / 1K |",
        "| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in output_table.to_dict(orient="records"):
        p95_text = "" if pd.isna(row["p95_latency_ms"]) else f"{float(row['p95_latency_ms']):.3f}"
        cost_text = "" if pd.isna(row["estimated_cost_per_1000_queries_usd"]) else f"${float(row['estimated_cost_per_1000_queries_usd']):.6f}"
        lines.append(
            f"| {int(row['rank'])} | `{row['model_name']}` | {row['selection_tier']} | {row['model_status']} | "
            f"{row['benchmark_verified']} | {row['eligible']} | {row['safety_candidate']} | "
            f"{float(row['accuracy']):.4f} | {float(row['macro_f1']):.4f} | "
            f"{float(row['false_short_circuit_rate']):.4f} | {float(row['short_circuit_recall']):.4f} | {p95_text} | {cost_text} |"
        )
    lines.extend([
        "",
        "## Decision order",
        "",
        "1. Require a real model, the identical frozen benchmark, and complete coverage.",
        "2. Prefer models passing all release guardrails.",
        "3. If none pass all guardrails, recommend the best real model that still passes the false-short-circuit safety ceiling and core quality floors.",
        "4. Rank within a selection tier by the frozen safety-weighted score.",
        "5. Use latency and cost as tie-breakers among comparable models.",
        "",
        "Diagnostic entries remain visible for transparency but cannot be recommended or packaged.",
    ])
    (args.output_dir / "SHOOTOUT_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(winner, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

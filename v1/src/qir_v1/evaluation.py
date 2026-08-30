from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

ROUTE_ORDER = ["short_circuit", "medium", "complex", "llm_needed"]


def _calibration_summary(confidence: pd.Series, correct: pd.Series, bins: int = 10) -> tuple[float | None, pd.DataFrame]:
    valid = confidence.notna()
    if not valid.any():
        return None, pd.DataFrame(
            columns=["lower", "upper", "count", "mean_confidence", "accuracy", "absolute_gap"]
        )
    conf = confidence.loc[valid].clip(0.0, 1.0)
    corr = correct.loc[valid].astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    records: list[dict[str, float | int]] = []
    weighted_gap = 0.0
    for index in range(bins):
        lower = float(edges[index])
        upper = float(edges[index + 1])
        if index == bins - 1:
            mask = conf.ge(lower) & conf.le(upper)
        else:
            mask = conf.ge(lower) & conf.lt(upper)
        count = int(mask.sum())
        if not count:
            continue
        mean_conf = float(conf.loc[mask].mean())
        accuracy = float(corr.loc[mask].mean())
        gap = abs(mean_conf - accuracy)
        weighted_gap += count / len(conf) * gap
        records.append(
            {
                "lower": lower,
                "upper": upper,
                "count": count,
                "mean_confidence": mean_conf,
                "accuracy": accuracy,
                "absolute_gap": gap,
            }
        )
    return float(weighted_gap), pd.DataFrame(records)


def evaluate_routes(
    gold: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    model_name: str,
    output_dir: Path | None = None,
    model_status: str = "real",
) -> dict[str, Any]:
    required_gold = {"benchmark_id", "query_text", "route"}
    required_pred = {"benchmark_id", "predicted_route", "confidence"}
    if missing := required_gold - set(gold.columns):
        raise ValueError(f"Gold data is missing columns: {sorted(missing)}")
    if missing := required_pred - set(predictions.columns):
        raise ValueError(f"Predictions are missing columns: {sorted(missing)}")
    if gold["benchmark_id"].duplicated().any():
        raise ValueError("Gold benchmark IDs are not unique")
    if predictions["benchmark_id"].duplicated().any():
        raise ValueError("Prediction benchmark IDs are not unique")

    merged = gold.merge(
        predictions,
        on="benchmark_id",
        how="left",
        suffixes=("_gold", "_pred"),
        validate="one_to_one",
    )
    coverage = float(merged["predicted_route"].notna().mean())
    if coverage < 1.0:
        missing_ids = merged.loc[merged["predicted_route"].isna(), "benchmark_id"].tolist()
        raise ValueError(f"Prediction coverage is {coverage:.3f}; missing {len(missing_ids)} benchmark IDs")

    unknown = set(merged["predicted_route"]) - set(ROUTE_ORDER)
    if unknown:
        raise ValueError(f"Predictions contain invalid routes: {sorted(unknown)}")

    y_true = merged["route"].astype(str)
    y_pred = merged["predicted_route"].astype(str)
    correct = y_true.eq(y_pred)
    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=ROUTE_ORDER, average="macro", zero_division=0))

    predicted_short = y_pred.eq("short_circuit")
    true_short = y_true.eq("short_circuit")
    false_short = predicted_short & ~true_short
    false_short_count = int(false_short.sum())
    predicted_short_count = int(predicted_short.sum())
    true_short_count = int(true_short.sum())
    false_short_rate = false_short_count / predicted_short_count if predicted_short_count else 0.0
    false_short_overall = false_short_count / len(merged) if len(merged) else 0.0
    short_precision = int((predicted_short & true_short).sum()) / predicted_short_count if predicted_short_count else 0.0
    short_recall = int((predicted_short & true_short).sum()) / true_short_count if true_short_count else 0.0

    latency = pd.to_numeric(merged.get("latency_ms", pd.Series(index=merged.index, dtype=float)), errors="coerce").dropna()
    cost = pd.to_numeric(
        merged.get("estimated_cost_usd", pd.Series(0.0, index=merged.index)), errors="coerce"
    ).fillna(0.0)
    confidence = pd.to_numeric(merged["confidence"], errors="coerce").clip(0.0, 1.0)
    calibration_error, calibration = _calibration_summary(confidence, correct)

    report = classification_report(
        y_true,
        y_pred,
        labels=ROUTE_ORDER,
        output_dict=True,
        zero_division=0,
    )
    per_route = {
        label: {
            "precision": float(report[label]["precision"]),
            "recall": float(report[label]["recall"]),
            "f1": float(report[label]["f1-score"]),
            "support": int(report[label]["support"]),
        }
        for label in ROUTE_ORDER
    }

    metrics: dict[str, Any] = {
        "schema_version": "1.0.0",
        "model_name": model_name,
        "model_status": model_status,
        "benchmark_rows": int(len(merged)),
        "coverage": coverage,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "false_short_circuit_rate": float(false_short_rate),
        "false_short_circuit_overall_rate": float(false_short_overall),
        "false_short_circuit_count": false_short_count,
        "predicted_short_circuit_count": predicted_short_count,
        "short_circuit_precision": float(short_precision),
        "short_circuit_recall": float(short_recall),
        "mean_confidence": float(confidence.mean()) if confidence.notna().any() else None,
        "expected_calibration_error": calibration_error,
        "median_latency_ms": float(latency.median()) if len(latency) else None,
        "p95_latency_ms": float(np.percentile(latency, 95)) if len(latency) else None,
        "mean_latency_ms": float(latency.mean()) if len(latency) else None,
        "total_estimated_cost_usd": float(cost.sum()),
        "estimated_cost_per_1000_queries_usd": float(cost.mean() * 1000) if len(cost) else 0.0,
        "per_route": per_route,
    }

    merged["correct"] = correct
    merged["false_short_circuit"] = false_short
    merged["confidence"] = confidence

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
        pd.DataFrame(report).transpose().to_csv(output_dir / "classification_report.csv")
        pd.DataFrame(
            confusion_matrix(y_true, y_pred, labels=ROUTE_ORDER),
            index=ROUTE_ORDER,
            columns=ROUTE_ORDER,
        ).to_csv(output_dir / "confusion_matrix.csv")
        calibration.to_csv(output_dir / "confidence_calibration.csv", index=False)
        merged.to_csv(output_dir / "predictions_enriched.csv", index=False)
        merged.loc[~merged["correct"]].sort_values(
            ["false_short_circuit", "confidence"], ascending=[False, False]
        ).to_csv(output_dir / "errors.csv", index=False)

        lines = [
            f"# {model_name} — V1 Benchmark Results",
            "",
            f"- Status: `{model_status}`",
            f"- Benchmark rows: **{len(merged)}**",
            f"- Accuracy: **{accuracy:.4f}**",
            f"- Macro F1: **{macro_f1:.4f}**",
            f"- False short-circuit rate: **{false_short_rate:.4f}** ({false_short_count}/{predicted_short_count})",
            f"- Short-circuit recall: **{short_recall:.4f}**",
            f"- Expected calibration error: **{calibration_error if calibration_error is not None else 'unavailable'}**",
            f"- Median latency: **{metrics['median_latency_ms']} ms**",
            f"- P95 latency: **{metrics['p95_latency_ms']} ms**",
            f"- Estimated cost per 1,000 queries: **${metrics['estimated_cost_per_1000_queries_usd']:.6f}**",
            "",
            "## Per-route metrics",
            "",
            "| Route | Precision | Recall | F1 | Support |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for label in ROUTE_ORDER:
            item = per_route[label]
            lines.append(
                f"| `{label}` | {item['precision']:.4f} | {item['recall']:.4f} | {item['f1']:.4f} | {item['support']} |"
            )
        lines.extend(
            [
                "",
                "## Safety metric",
                "",
                "False short-circuit rate is the share of queries predicted as `short_circuit` whose true route is not `short_circuit`. This is the primary dangerous-routing metric.",
            ]
        )
        (output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return metrics

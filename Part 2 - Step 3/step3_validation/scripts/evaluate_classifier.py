from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from step3_validation.common import (  # noqa: E402
    CONFIDENCE_BAND_LABELS,
    confidence_band,
    derive_route_tier,
    derive_short_circuit,
    ensure_unique_join_keys,
    format_num,
    format_pct,
    html_escape_table,
    join_key,
    load_csv,
    load_route_config,
    normalized,
    parse_float,
    quantile,
    require_columns,
    safe_rate,
    write_csv,
    write_json,
)

THRESHOLDS = {
    "intent_accuracy": 0.90,
    "persona_accuracy": 0.85,
    "joint_accuracy": 0.80,
    "route_tier_accuracy": 0.90,
    "short_circuit_precision": 0.95,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate classifier predictions against step 3 benchmark labels."
    )
    parser.add_argument("--labels", required=True, help="Path to benchmark_gold.csv.")
    parser.add_argument("--predictions", required=True, help="Path to the prediction export CSV.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated reports.")
    parser.add_argument(
        "--route-config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "intent_to_route_tier.json"),
        help="Path to the intent-to-route-tier mapping JSON.",
    )
    return parser.parse_args()


def accuracy_by_group(
    rows: list[dict[str, object]],
    *,
    group_key: str,
    correct_key: str,
) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row[group_key])].append(row)
    result: dict[str, dict[str, float | int]] = {}
    for group_name, group_rows in sorted(groups.items()):
        total = len(group_rows)
        correct = sum(1 for row in group_rows if bool(row[correct_key]))
        result[group_name] = {
            "count": total,
            "accuracy": safe_rate(correct, total),
        }
    return result


def build_confusion_matrix(
    rows: list[dict[str, object]],
    *,
    gold_key: str,
    predicted_key: str,
) -> dict[str, dict[str, int]]:
    labels = sorted({str(row[gold_key]) for row in rows} | {str(row[predicted_key]) for row in rows})
    matrix = {gold: {predicted: 0 for predicted in labels} for gold in labels}
    for row in rows:
        matrix[str(row[gold_key])][str(row[predicted_key])] += 1
    return matrix


def top_confusions(
    matrix: dict[str, dict[str, int]],
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for gold, predicted_counts in matrix.items():
        total = sum(predicted_counts.values())
        if total == 0:
            continue
        for predicted, count in predicted_counts.items():
            if gold == predicted or count == 0:
                continue
            pairs.append(
                {
                    "gold": gold,
                    "predicted": predicted,
                    "count": count,
                    "row_rate": safe_rate(count, total),
                }
            )
    pairs.sort(key=lambda item: (-int(item["count"]), -float(item["row_rate"]), str(item["gold"]), str(item["predicted"])))
    return pairs[:limit]


def evaluate_thresholds(metrics: dict[str, float]) -> dict[str, object]:
    checks = {}
    for metric_name, threshold in THRESHOLDS.items():
        actual = float(metrics[metric_name])
        checks[metric_name] = {
            "threshold": threshold,
            "actual": actual,
            "passed": actual >= threshold,
        }
    overall_passed = all(bool(check["passed"]) for check in checks.values())
    return {
        "overall_passed": overall_passed,
        "checks": checks,
    }


def build_recommendations(
    *,
    matched_rows: list[dict[str, object]],
    missing_predictions: list[dict[str, str]],
    persona_accuracy: float,
    intent_accuracy: float,
    route_tier_accuracy: float,
    short_circuit_precision: float,
    per_persona_accuracy: dict[str, dict[str, float | int]],
    per_intent_accuracy: dict[str, dict[str, float | int]],
    persona_confusions: list[dict[str, object]],
    intent_confusions: list[dict[str, object]],
    unknown_predicted_intents: list[str],
) -> list[str]:
    recommendations: list[str] = []

    if intent_accuracy < 0.90:
        recommendations.append(
            "Intent accuracy is below the 90% baseline. Review low-performing intents before treating the classifier as production-ready."
        )
    else:
        recommendations.append(
            "Intent accuracy meets the 90% baseline. Keep the current schema unless repeated confusion pairs remain operationally costly."
        )

    if persona_accuracy < 0.85:
        recommendations.append(
            "Persona accuracy is below the 85% support threshold. Tighten persona definitions or add clearer training examples."
        )

    if route_tier_accuracy < 0.90:
        recommendations.append(
            "Derived route-tier accuracy is below 90%. Do not trust routing directly from classifier output until the weak intents are fixed."
        )

    if short_circuit_precision < 0.95:
        recommendations.append(
            "Short-circuit precision is below 95%. Shortcut routing is not yet safe without a stricter gate."
        )

    low_persona_slices = [
        persona
        for persona, stats in per_persona_accuracy.items()
        if int(stats["count"]) >= 2 and float(stats["accuracy"]) < 0.80
    ]
    if low_persona_slices:
        recommendations.append(
            f"Review persona slices with weak accuracy: {', '.join(low_persona_slices[:5])}."
        )

    low_intent_slices = [
        intent
        for intent, stats in per_intent_accuracy.items()
        if int(stats["count"]) >= 2 and float(stats["accuracy"]) < 0.80
    ]
    if low_intent_slices:
        recommendations.append(
            f"Review or rewrite low-performing intents: {', '.join(low_intent_slices[:5])}."
        )

    if persona_confusions:
        pair = persona_confusions[0]
        if int(pair["count"]) >= 2:
            recommendations.append(
                "Top persona confusion pair suggests either weak persona definitions or insufficient examples: "
                f"{pair['gold']} vs {pair['predicted']}."
            )

    if intent_confusions:
        pair = intent_confusions[0]
        if int(pair["count"]) >= 2:
            recommendations.append(
                "Top intent confusion pair suggests a label-boundary review: "
                f"{pair['gold']} vs {pair['predicted']}."
            )

    if unknown_predicted_intents:
        recommendations.append(
            "Predictions included intents outside the checked-in route mapping: "
            f"{', '.join(unknown_predicted_intents[:5])}. Those rows were forced to fallback."
        )

    if missing_predictions:
        recommendations.append(
            f"{len(missing_predictions)} benchmark rows were missing predictions. Fix export completeness before trusting the metrics."
        )

    if not recommendations:
        recommendations.append("No immediate label merge recommendation was triggered by the current metrics.")

    return recommendations


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def sort_accuracy_map(stats: dict[str, dict[str, float | int]]) -> list[tuple[str, dict[str, float | int]]]:
    return sorted(
        stats.items(),
        key=lambda item: (float(item[1]["accuracy"]), -int(item[1]["count"]), item[0]),
    )


def build_label_refinement_candidates(
    *,
    per_persona_accuracy: dict[str, dict[str, float | int]],
    per_intent_accuracy: dict[str, dict[str, float | int]],
    persona_confusions: list[dict[str, object]],
    intent_confusions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "persona_slices_below_0_80": [
            {
                "persona": persona,
                "count": int(stats["count"]),
                "accuracy": float(stats["accuracy"]),
            }
            for persona, stats in sort_accuracy_map(per_persona_accuracy)
            if int(stats["count"]) >= 2 and float(stats["accuracy"]) < 0.80
        ],
        "intent_slices_below_0_80": [
            {
                "intent": intent,
                "count": int(stats["count"]),
                "accuracy": float(stats["accuracy"]),
            }
            for intent, stats in sort_accuracy_map(per_intent_accuracy)
            if int(stats["count"]) >= 2 and float(stats["accuracy"]) < 0.80
        ],
        "top_persona_confusions": persona_confusions[:5],
        "top_intent_confusions": intent_confusions[:5],
    }


def confusion_matrix_rows(matrix: dict[str, dict[str, int]]) -> tuple[list[str], list[list[str]]]:
    labels = sorted(matrix)
    headers = ["Gold \\ Predicted", *labels]
    rows = []
    for gold in labels:
        rows.append([gold, *[str(matrix[gold].get(predicted, 0)) for predicted in labels]])
    return headers, rows


def render_markdown_report(summary: dict[str, object]) -> str:
    dataset = summary["dataset"]
    metrics = summary["metrics"]
    latency = summary["latency_ms"]
    tokens = summary["tokens"]
    cost = summary["cost_usd"]
    route_distribution = summary["distribution"]["gold_route_tiers"]
    join_methods = summary["distribution"]["join_methods"]
    per_persona_accuracy = summary["distribution"]["per_persona_accuracy"]
    per_intent_accuracy = summary["distribution"]["per_intent_accuracy"]
    persona_confusion = summary["confusion_matrices"]["persona"]
    intent_confusion = summary["confusion_matrices"]["intent"]
    route_tier_confusion = summary["confusion_matrices"]["route_tier"]
    acceptance = summary["acceptance"]
    operating_counts = summary["operating_counts"]
    routing_health = summary["routing_health"]
    top_persona_confusions = summary["top_persona_confusions"]
    top_intent_confusions = summary["top_intent_confusions"]

    report_lines = [
        "# Step 3 Evaluation Report",
        "",
        "## Dataset Coverage",
        f"- Labels: {dataset['total_labels']}",
        f"- Matched predictions: {dataset['matched_predictions']}",
        f"- Missing predictions: {dataset['missing_predictions']}",
        f"- Matched by row_id: {dataset['matched_by_row_id']}",
        f"- Matched by query fallback: {dataset['matched_by_query']}",
        "- Join method distribution: "
        + ", ".join(f"{name}={count}" for name, count in sorted(join_methods.items())),
        "",
        "## Core Metrics",
        f"- Persona accuracy: {format_pct(metrics['persona_accuracy'])}",
        f"- Intent accuracy: {format_pct(metrics['intent_accuracy'])}",
        f"- Joint accuracy: {format_pct(metrics['joint_accuracy'])}",
        f"- Route-tier accuracy: {format_pct(metrics['route_tier_accuracy'])}",
        f"- Short-circuit precision: {format_pct(metrics['short_circuit_precision'])}",
        f"- Short-circuit recall: {format_pct(metrics['short_circuit_recall'])}",
        f"- Short-circuit boolean accuracy: {format_pct(metrics['short_circuit_boolean_accuracy'])}",
        "",
        "## Latency",
        f"- Average latency: {format_num(latency['avg'])} ms",
        f"- P50 latency: {format_num(latency['p50'])} ms",
        f"- P95 latency: {format_num(latency['p95'])} ms",
        f"- Max latency: {format_num(latency['max'])} ms",
        "",
        "## Tokens And Cost",
        f"- Average total tokens: {format_num(tokens['avg_total_tokens'])}",
        f"- Total tokens: {format_num(tokens['total_tokens'])}",
        f"- Total cost: ${cost['total']:.6f}",
        f"- Average cost per query: ${cost['avg']:.6f}",
        "",
        "## Acceptance Status",
        f"- Overall status: {'PASS' if acceptance['overall_passed'] else 'FAIL'}",
        "",
        markdown_table(
            ["Metric", "Actual", "Threshold", "Passed"],
            [
                [
                    metric_name,
                    format_pct(float(check["actual"])),
                    format_pct(float(check["threshold"])),
                    "yes" if bool(check["passed"]) else "no",
                ]
                for metric_name, check in acceptance["checks"].items()
            ],
        ),
        "",
        "## Route Tier Distribution",
    ]
    for route_tier, count in route_distribution.items():
        report_lines.append(f"- {route_tier}: {count}")

    report_lines.extend(["", "## Confidence Bands"])
    for band in CONFIDENCE_BAND_LABELS:
        band_stats = summary["confidence_bands"][band]
        report_lines.append(
            f"- {band}: count={band_stats['count']}, intent_accuracy={format_pct(band_stats['intent_accuracy'])}, route_tier_accuracy={format_pct(band_stats['route_tier_accuracy'])}"
        )

    report_lines.extend(
        [
            "",
            "## Operating Counts",
            f"- Proceed high-confidence: {operating_counts['proceed_high_confidence']}",
            f"- Proceed medium-confidence: {operating_counts['proceed_medium_confidence']}",
            f"- Escalate low-confidence: {operating_counts['escalate_low_confidence']}",
            f"- Fallback insufficient-confidence: {operating_counts['fallback_insufficient_confidence']}",
            f"- Fallback unknown-intent: {operating_counts['fallback_unknown_intent']}",
        ]
    )

    report_lines.extend(["", "## Routing Health"])
    report_lines.append(
        f"- Route-mapping fallback threshold: {routing_health['fallback_confidence_below']:.2f}"
    )
    report_lines.append(
        f"- Unknown predicted intent count: {routing_health['unknown_predicted_intent_count']}"
    )
    if routing_health["unknown_predicted_intents"]:
        report_lines.append(
            "- Unknown predicted intents: "
            + ", ".join(routing_health["unknown_predicted_intents"])
        )
    else:
        report_lines.append("- Unknown predicted intents: none")

    report_lines.extend(["", "## Recommendations"])
    for recommendation in summary["recommendations"]:
        report_lines.append(f"- {recommendation}")

    report_lines.extend(["", "## Worst-Performing Personas"])
    persona_rows = [
        [name, str(stats["count"]), format_pct(float(stats["accuracy"]))]
        for name, stats in sort_accuracy_map(per_persona_accuracy)[:5]
    ]
    report_lines.append(markdown_table(["Persona", "Count", "Accuracy"], persona_rows))

    report_lines.extend(["", "## Worst-Performing Intents"])
    intent_rows = [
        [name, str(stats["count"]), format_pct(float(stats["accuracy"]))]
        for name, stats in sort_accuracy_map(per_intent_accuracy)[:8]
    ]
    report_lines.append(markdown_table(["Intent", "Count", "Accuracy"], intent_rows))

    report_lines.extend(["", "## Top Persona Confusions"])
    persona_confusion_rows = [
        [row["gold"], row["predicted"], str(row["count"]), format_pct(float(row["row_rate"]))]
        for row in top_persona_confusions
    ]
    if persona_confusion_rows:
        report_lines.append(
            markdown_table(["Gold Persona", "Predicted Persona", "Count", "Row Rate"], persona_confusion_rows)
        )
    else:
        report_lines.append("- None")

    report_lines.extend(["", "## Top Intent Confusions"])
    intent_confusion_rows = [
        [row["gold"], row["predicted"], str(row["count"]), format_pct(float(row["row_rate"]))]
        for row in top_intent_confusions
    ]
    if intent_confusion_rows:
        report_lines.append(
            markdown_table(["Gold Intent", "Predicted Intent", "Count", "Row Rate"], intent_confusion_rows)
        )
    else:
        report_lines.append("- None")

    report_lines.extend(["", "## Persona Confusion Matrix"])
    headers, rows = confusion_matrix_rows(persona_confusion)
    report_lines.append(markdown_table(headers, rows))

    report_lines.extend(["", "## Intent Confusion Matrix"])
    headers, rows = confusion_matrix_rows(intent_confusion)
    report_lines.append(markdown_table(headers, rows))

    report_lines.extend(["", "## Route Tier Confusion Matrix"])
    headers, rows = confusion_matrix_rows(route_tier_confusion)
    report_lines.append(markdown_table(headers, rows))

    report_lines.extend(["", "## Highest Confidence Wrong Predictions"])
    for row in summary["highest_confidence_wrong_predictions"]:
        report_lines.append(
            f"- {row['row_id']}: confidence={row['predicted_confidence']}, query={row['query']}"
        )

    return "\n".join(report_lines) + "\n"


def render_html_report(summary: dict[str, object]) -> str:
    dataset = summary["dataset"]
    metrics = summary["metrics"]
    per_persona_accuracy = summary["distribution"]["per_persona_accuracy"]
    per_intent_accuracy = summary["distribution"]["per_intent_accuracy"]
    persona_confusion = summary["confusion_matrices"]["persona"]
    intent_confusion = summary["confusion_matrices"]["intent"]
    route_tier_confusion = summary["confusion_matrices"]["route_tier"]
    acceptance = summary["acceptance"]
    operating_counts = summary["operating_counts"]
    routing_health = summary["routing_health"]
    top_persona_confusions = summary["top_persona_confusions"]
    top_intent_confusions = summary["top_intent_confusions"]
    confidence_rows = []
    for band in CONFIDENCE_BAND_LABELS:
        band_stats = summary["confidence_bands"][band]
        confidence_rows.append(
            [
                band,
                str(band_stats["count"]),
                format_pct(float(band_stats["intent_accuracy"])),
                format_pct(float(band_stats["joint_accuracy"])),
                format_pct(float(band_stats["route_tier_accuracy"])),
            ]
        )

    recommendations_html = "".join(
        f"<li>{recommendation}</li>" for recommendation in summary["recommendations"]
    )
    persona_rows = [
        [name, str(stats["count"]), format_pct(float(stats["accuracy"]))]
        for name, stats in sort_accuracy_map(per_persona_accuracy)[:5]
    ]
    intent_rows = [
        [name, str(stats["count"]), format_pct(float(stats["accuracy"]))]
        for name, stats in sort_accuracy_map(per_intent_accuracy)[:8]
    ]
    acceptance_rows = [
        [
            metric_name,
            format_pct(float(check["actual"])),
            format_pct(float(check["threshold"])),
            "yes" if bool(check["passed"]) else "no",
        ]
        for metric_name, check in acceptance["checks"].items()
    ]

    highest_confidence_rows = [
        [
            str(row["row_id"]),
            str(row["predicted_confidence"]),
            str(row["gold_persona"]),
            str(row["predicted_persona"]),
            str(row["gold_intent"]),
            str(row["predicted_intent"]),
            str(row["query"]),
        ]
        for row in summary["highest_confidence_wrong_predictions"]
    ]
    top_persona_confusion_rows = [
        [str(row["gold"]), str(row["predicted"]), str(row["count"]), format_pct(float(row["row_rate"]))]
        for row in top_persona_confusions
    ]
    top_intent_confusion_rows = [
        [str(row["gold"]), str(row["predicted"]), str(row["count"]), format_pct(float(row["row_rate"]))]
        for row in top_intent_confusions
    ]
    persona_headers, persona_matrix_rows = confusion_matrix_rows(persona_confusion)
    intent_headers, intent_matrix_rows = confusion_matrix_rows(intent_confusion)
    route_headers, route_matrix_rows = confusion_matrix_rows(route_tier_confusion)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Step 3 Evaluation Dashboard</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 32px;
      color: #1f2937;
      background: #f8fafc;
    }}
    h1, h2 {{
      margin-bottom: 12px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }}
    .card {{
      background: white;
      border: 1px solid #dbe2ea;
      border-radius: 10px;
      padding: 16px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }}
    .metric {{
      font-size: 1.6rem;
      font-weight: 700;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
      margin-bottom: 24px;
    }}
    th, td {{
      border: 1px solid #dbe2ea;
      text-align: left;
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
    }}
    ul {{
      background: white;
      border: 1px solid #dbe2ea;
      border-radius: 10px;
      padding: 16px 28px;
    }}
  </style>
</head>
<body>
  <h1>Step 3 Evaluation Dashboard</h1>
  <div class="grid">
    <div class="card"><div>Persona Accuracy</div><div class="metric">{format_pct(float(metrics["persona_accuracy"]))}</div></div>
    <div class="card"><div>Intent Accuracy</div><div class="metric">{format_pct(float(metrics["intent_accuracy"]))}</div></div>
    <div class="card"><div>Joint Accuracy</div><div class="metric">{format_pct(float(metrics["joint_accuracy"]))}</div></div>
    <div class="card"><div>Route Tier Accuracy</div><div class="metric">{format_pct(float(metrics["route_tier_accuracy"]))}</div></div>
    <div class="card"><div>Short-Circuit Precision</div><div class="metric">{format_pct(float(metrics["short_circuit_precision"]))}</div></div>
    <div class="card"><div>Missing Predictions</div><div class="metric">{dataset["missing_predictions"]}</div></div>
  </div>
  <h2>Join Integrity</h2>
  {html_escape_table(
      ["Category", "Count"],
      [
          ["Matched by row_id", str(dataset["matched_by_row_id"])],
          ["Matched by query fallback", str(dataset["matched_by_query"])],
      ],
  )}
  <h2>Acceptance Status</h2>
  <p><strong>Overall:</strong> {"PASS" if acceptance["overall_passed"] else "FAIL"}</p>
  {html_escape_table(["Metric", "Actual", "Threshold", "Passed"], acceptance_rows)}
  <h2>Confidence Bands</h2>
  {html_escape_table(["Band", "Count", "Intent Accuracy", "Joint Accuracy", "Route Tier Accuracy"], confidence_rows)}
  <h2>Operating Counts</h2>
  {html_escape_table(
      ["Category", "Count"],
      [
          ["Proceed high-confidence", str(operating_counts["proceed_high_confidence"])],
          ["Proceed medium-confidence", str(operating_counts["proceed_medium_confidence"])],
          ["Escalate low-confidence", str(operating_counts["escalate_low_confidence"])],
          ["Fallback insufficient-confidence", str(operating_counts["fallback_insufficient_confidence"])],
          ["Fallback unknown-intent", str(operating_counts["fallback_unknown_intent"])],
      ],
  )}
  <h2>Routing Health</h2>
  {html_escape_table(
      ["Signal", "Value"],
      [
          ["Fallback threshold", f"{float(routing_health['fallback_confidence_below']):.2f}"],
          ["Unknown predicted intent count", str(routing_health["unknown_predicted_intent_count"])],
          ["Unknown predicted intents", ", ".join(routing_health["unknown_predicted_intents"]) or "none"],
      ],
  )}
  <h2>Recommendations</h2>
  <ul>{recommendations_html}</ul>
  <h2>Worst-Performing Personas</h2>
  {html_escape_table(["Persona", "Count", "Accuracy"], persona_rows)}
  <h2>Worst-Performing Intents</h2>
  {html_escape_table(["Intent", "Count", "Accuracy"], intent_rows)}
  <h2>Top Persona Confusions</h2>
  {html_escape_table(["Gold Persona", "Predicted Persona", "Count", "Row Rate"], top_persona_confusion_rows)}
  <h2>Top Intent Confusions</h2>
  {html_escape_table(["Gold Intent", "Predicted Intent", "Count", "Row Rate"], top_intent_confusion_rows)}
  <h2>Persona Confusion Matrix</h2>
  {html_escape_table(persona_headers, persona_matrix_rows)}
  <h2>Intent Confusion Matrix</h2>
  {html_escape_table(intent_headers, intent_matrix_rows)}
  <h2>Route Tier Confusion Matrix</h2>
  {html_escape_table(route_headers, route_matrix_rows)}
  <h2>Highest Confidence Wrong Predictions</h2>
  {html_escape_table(["Row ID", "Confidence", "Gold Persona", "Pred Persona", "Gold Intent", "Pred Intent", "Query"], highest_confidence_rows)}
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    labels_path = Path(args.labels)
    predictions_path = Path(args.predictions)
    output_dir = Path(args.output_dir)
    route_config = load_route_config(Path(args.route_config))
    output_dir.mkdir(parents=True, exist_ok=True)

    label_rows = load_csv(labels_path)
    prediction_rows = load_csv(predictions_path)
    if not label_rows:
        raise ValueError("Labels file is empty.")
    if not prediction_rows:
        raise ValueError("Predictions file is empty.")

    label_columns = require_columns(
        list(label_rows[0].keys()),
        {
            "row_id": ["row_id"],
            "query": ["query", "Query"],
            "gold_persona": ["gold_persona", "Persona"],
            "gold_intent": ["gold_intent", "Intent"],
        },
    )
    prediction_columns = require_columns(
        list(prediction_rows[0].keys()),
        {
            "predicted_persona": ["predicted_persona"],
            "predicted_intent": ["predicted_intent"],
            "predicted_confidence": ["predicted_confidence"],
        },
    )

    ensure_unique_join_keys(label_rows, source_name="labels")
    ensure_unique_join_keys(prediction_rows, source_name="predictions")

    route_mapping = route_config["intent_to_route_tier"]
    if not isinstance(route_mapping, dict):
        raise ValueError("Route config 'intent_to_route_tier' must be a JSON object.")
    known_intents = {normalized(intent) for intent in route_mapping}
    fallback_threshold = float(route_config["fallback_confidence_below"])

    unknown_gold_intents = sorted(
        {
            normalized(label_row[label_columns["gold_intent"]])
            for label_row in label_rows
            if normalized(label_row[label_columns["gold_intent"]]) not in known_intents
        }
    )
    if unknown_gold_intents:
        raise ValueError(
            "Benchmark labels contain intents that are missing from the route mapping: "
            + ", ".join(unknown_gold_intents[:10])
        )

    predictions_by_key = {join_key(row): row for row in prediction_rows}
    label_query_counts = Counter(
        f"query:{normalized(label_row[label_columns['query']]).lower()}"
        for label_row in label_rows
    )
    prediction_query_counts = Counter(
        f"query:{normalized(prediction_row.get('query')).lower()}"
        for prediction_row in prediction_rows
        if normalized(prediction_row.get("query"))
    )

    matched_rows: list[dict[str, object]] = []
    missing_predictions: list[dict[str, str]] = []
    matched_by_row_id = 0
    matched_by_query = 0
    for label_row in label_rows:
        primary_key = join_key(label_row)
        query_fallback_key = f"query:{normalized(label_row.get(label_columns['query'])).lower()}"
        join_method = "row_id"
        prediction_row = predictions_by_key.get(primary_key)
        if prediction_row is None and primary_key != query_fallback_key:
            if label_query_counts[query_fallback_key] > 1:
                raise ValueError(
                    "Query-based fallback is ambiguous because the benchmark contains duplicate query strings "
                    f"for '{normalized(label_row.get(label_columns['query']))}'. Provide row_id-based predictions."
                )
            if prediction_query_counts[query_fallback_key] > 1:
                raise ValueError(
                    "Query-based fallback is ambiguous because the prediction export contains duplicate query strings "
                    f"for '{normalized(label_row.get(label_columns['query']))}'."
                )
            prediction_row = predictions_by_key.get(query_fallback_key)
            if prediction_row is not None:
                join_method = "query"
        if prediction_row is None:
            missing_predictions.append(label_row)
            continue
        if join_method == "row_id":
            matched_by_row_id += 1
        else:
            matched_by_query += 1

        gold_persona = normalized(label_row[label_columns["gold_persona"]])
        gold_intent = normalized(label_row[label_columns["gold_intent"]])
        gold_route_tier = derive_route_tier(
            intent=gold_intent,
            confidence=None,
            config=route_config,
            apply_confidence_fallback=False,
        )
        gold_short_circuit = derive_short_circuit(gold_route_tier)

        predicted_persona = normalized(prediction_row[prediction_columns["predicted_persona"]])
        predicted_intent = normalized(prediction_row[prediction_columns["predicted_intent"]])
        predicted_confidence = parse_float(prediction_row[prediction_columns["predicted_confidence"]])
        if predicted_confidence is None:
            raise ValueError(
                f"Prediction row {primary_key} is missing predicted_confidence."
            )
        predicted_intent_known = predicted_intent in known_intents
        fallback_due_to_confidence = predicted_confidence < fallback_threshold
        fallback_due_to_unknown_intent = not predicted_intent_known and not fallback_due_to_confidence
        predicted_route_tier = derive_route_tier(
            intent=predicted_intent,
            confidence=predicted_confidence,
            config=route_config,
            apply_confidence_fallback=True,
        )
        predicted_short_circuit = derive_short_circuit(predicted_route_tier)

        persona_correct = gold_persona == predicted_persona
        intent_correct = gold_intent == predicted_intent
        joint_correct = persona_correct and intent_correct
        route_tier_correct = gold_route_tier == predicted_route_tier
        short_circuit_correct = gold_short_circuit == predicted_short_circuit

        error_types = []
        if not persona_correct:
            error_types.append("persona_mismatch")
        if not intent_correct:
            error_types.append("intent_mismatch")
        if not route_tier_correct:
            error_types.append("route_tier_mismatch")
        if not short_circuit_correct:
            error_types.append("short_circuit_mismatch")

        matched_rows.append(
            {
                "row_id": normalized(label_row[label_columns["row_id"]]),
                "query": normalized(label_row[label_columns["query"]]),
                "gold_persona": gold_persona,
                "predicted_persona": predicted_persona,
                "gold_intent": gold_intent,
                "predicted_intent": predicted_intent,
                "gold_route_tier": gold_route_tier,
                "predicted_route_tier": predicted_route_tier,
                "gold_short_circuit": gold_short_circuit,
                "predicted_short_circuit": predicted_short_circuit,
                "predicted_confidence": predicted_confidence,
                "join_method": join_method,
                "predicted_intent_known": predicted_intent_known,
                "fallback_due_to_confidence": fallback_due_to_confidence,
                "fallback_due_to_unknown_intent": fallback_due_to_unknown_intent,
                "gold_entities_json": normalized(label_row.get("gold_entities_json")),
                "predicted_entities_json": normalized(prediction_row.get("predicted_entities_json")),
                "model": normalized(prediction_row.get("model")),
                "latency_ms": parse_float(prediction_row.get("latency_ms")),
                "prompt_tokens": parse_float(prediction_row.get("prompt_tokens")),
                "completion_tokens": parse_float(prediction_row.get("completion_tokens")),
                "total_tokens": parse_float(prediction_row.get("total_tokens")),
                "estimated_cost_usd": parse_float(prediction_row.get("estimated_cost_usd")),
                "persona_correct": persona_correct,
                "intent_correct": intent_correct,
                "joint_correct": joint_correct,
                "route_tier_correct": route_tier_correct,
                "short_circuit_correct": short_circuit_correct,
                "error_types": ";".join(error_types),
            }
        )

    matched_count = len(matched_rows)
    if matched_count == 0:
        raise ValueError("No predictions matched the benchmark labels.")

    persona_accuracy = safe_rate(sum(1 for row in matched_rows if row["persona_correct"]), matched_count)
    intent_accuracy = safe_rate(sum(1 for row in matched_rows if row["intent_correct"]), matched_count)
    joint_accuracy = safe_rate(sum(1 for row in matched_rows if row["joint_correct"]), matched_count)
    route_tier_accuracy = safe_rate(sum(1 for row in matched_rows if row["route_tier_correct"]), matched_count)

    tp = sum(1 for row in matched_rows if row["gold_short_circuit"] and row["predicted_short_circuit"])
    tn = sum(1 for row in matched_rows if not row["gold_short_circuit"] and not row["predicted_short_circuit"])
    fp = sum(1 for row in matched_rows if not row["gold_short_circuit"] and row["predicted_short_circuit"])
    fn = sum(1 for row in matched_rows if row["gold_short_circuit"] and not row["predicted_short_circuit"])

    short_circuit_precision = safe_rate(tp, tp + fp)
    short_circuit_recall = safe_rate(tp, tp + fn)
    short_circuit_boolean_accuracy = safe_rate(tp + tn, matched_count)

    confidence_summary: dict[str, dict[str, float | int]] = {}
    for band in CONFIDENCE_BAND_LABELS:
        band_rows = [row for row in matched_rows if confidence_band(float(row["predicted_confidence"])) == band]
        band_total = len(band_rows)
        confidence_summary[band] = {
            "count": band_total,
            "coverage": safe_rate(band_total, matched_count),
            "persona_accuracy": safe_rate(sum(1 for row in band_rows if row["persona_correct"]), band_total),
            "intent_accuracy": safe_rate(sum(1 for row in band_rows if row["intent_correct"]), band_total),
            "joint_accuracy": safe_rate(sum(1 for row in band_rows if row["joint_correct"]), band_total),
            "route_tier_accuracy": safe_rate(sum(1 for row in band_rows if row["route_tier_correct"]), band_total),
        }

    operating_counts = {
        "proceed_high_confidence": confidence_summary["0.85-1.00"]["count"],
        "proceed_medium_confidence": confidence_summary["0.65-0.84"]["count"],
        "escalate_low_confidence": confidence_summary["0.40-0.64"]["count"],
        "fallback_insufficient_confidence": confidence_summary["<0.40"]["count"],
        "fallback_unknown_intent": sum(
            1 for row in matched_rows if bool(row["fallback_due_to_unknown_intent"])
        ),
    }

    latencies = [float(row["latency_ms"]) for row in matched_rows if row["latency_ms"] is not None]
    prompt_tokens = [float(row["prompt_tokens"]) for row in matched_rows if row["prompt_tokens"] is not None]
    completion_tokens = [float(row["completion_tokens"]) for row in matched_rows if row["completion_tokens"] is not None]
    total_tokens = [float(row["total_tokens"]) for row in matched_rows if row["total_tokens"] is not None]
    costs = [float(row["estimated_cost_usd"]) for row in matched_rows if row["estimated_cost_usd"] is not None]

    per_persona_accuracy = accuracy_by_group(
        matched_rows,
        group_key="gold_persona",
        correct_key="persona_correct",
    )
    per_intent_accuracy = accuracy_by_group(
        matched_rows,
        group_key="gold_intent",
        correct_key="intent_correct",
    )

    persona_confusion = build_confusion_matrix(
        matched_rows,
        gold_key="gold_persona",
        predicted_key="predicted_persona",
    )
    persona_confusions = top_confusions(persona_confusion)
    intent_confusion = build_confusion_matrix(
        matched_rows,
        gold_key="gold_intent",
        predicted_key="predicted_intent",
    )
    route_tier_confusion = build_confusion_matrix(
        matched_rows,
        gold_key="gold_route_tier",
        predicted_key="predicted_route_tier",
    )

    highest_confidence_wrong_predictions = sorted(
        [row for row in matched_rows if not row["joint_correct"]],
        key=lambda row: (-float(row["predicted_confidence"]), str(row["row_id"])),
    )[:10]
    highest_confidence_serializable = [
        {
            "row_id": row["row_id"],
            "query": row["query"],
            "predicted_confidence": row["predicted_confidence"],
            "gold_persona": row["gold_persona"],
            "predicted_persona": row["predicted_persona"],
            "gold_intent": row["gold_intent"],
            "predicted_intent": row["predicted_intent"],
            "error_types": row["error_types"],
        }
        for row in highest_confidence_wrong_predictions
    ]

    intent_confusions = top_confusions(intent_confusion)
    unknown_predicted_intents = sorted(
        {
            str(row["predicted_intent"])
            for row in matched_rows
            if not bool(row["predicted_intent_known"])
        }
    )
    recommendations = build_recommendations(
        matched_rows=matched_rows,
        missing_predictions=missing_predictions,
        persona_accuracy=persona_accuracy,
        intent_accuracy=intent_accuracy,
        route_tier_accuracy=route_tier_accuracy,
        short_circuit_precision=short_circuit_precision,
        per_persona_accuracy=per_persona_accuracy,
        per_intent_accuracy=per_intent_accuracy,
        persona_confusions=persona_confusions,
        intent_confusions=intent_confusions,
        unknown_predicted_intents=unknown_predicted_intents,
    )
    label_refinement_candidates = build_label_refinement_candidates(
        per_persona_accuracy=per_persona_accuracy,
        per_intent_accuracy=per_intent_accuracy,
        persona_confusions=persona_confusions,
        intent_confusions=intent_confusions,
    )

    distributions = {
        "gold_personas": Counter(str(row["gold_persona"]) for row in matched_rows),
        "predicted_personas": Counter(str(row["predicted_persona"]) for row in matched_rows),
        "gold_intents": Counter(str(row["gold_intent"]) for row in matched_rows),
        "predicted_intents": Counter(str(row["predicted_intent"]) for row in matched_rows),
        "gold_route_tiers": Counter(str(row["gold_route_tier"]) for row in matched_rows),
        "predicted_route_tiers": Counter(str(row["predicted_route_tier"]) for row in matched_rows),
        "models": Counter(str(row["model"]) for row in matched_rows if row["model"]),
        "join_methods": Counter(str(row["join_method"]) for row in matched_rows),
        "per_persona_accuracy": per_persona_accuracy,
        "per_intent_accuracy": per_intent_accuracy,
    }

    summary = {
        "dataset": {
            "total_labels": len(label_rows),
            "matched_predictions": matched_count,
            "missing_predictions": len(missing_predictions),
            "missing_prediction_row_ids": [normalized(row.get("row_id")) for row in missing_predictions],
            "matched_by_row_id": matched_by_row_id,
            "matched_by_query": matched_by_query,
        },
        "metrics": {
            "persona_accuracy": persona_accuracy,
            "intent_accuracy": intent_accuracy,
            "joint_accuracy": joint_accuracy,
            "route_tier_accuracy": route_tier_accuracy,
            "short_circuit_precision": short_circuit_precision,
            "short_circuit_recall": short_circuit_recall,
            "short_circuit_boolean_accuracy": short_circuit_boolean_accuracy,
            "short_circuit_confusion": {
                "true_positive": tp,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
            },
        },
        "latency_ms": {
            "count": len(latencies),
            "avg": safe_rate(sum(latencies), len(latencies)),
            "p50": quantile(latencies, 0.50),
            "p95": quantile(latencies, 0.95),
            "max": max(latencies) if latencies else 0.0,
        },
        "tokens": {
            "avg_prompt_tokens": safe_rate(sum(prompt_tokens), len(prompt_tokens)),
            "avg_completion_tokens": safe_rate(sum(completion_tokens), len(completion_tokens)),
            "avg_total_tokens": safe_rate(sum(total_tokens), len(total_tokens)),
            "total_tokens": sum(total_tokens),
        },
        "cost_usd": {
            "total": sum(costs),
            "avg": safe_rate(sum(costs), len(costs)),
        },
        "confidence_bands": confidence_summary,
        "operating_counts": operating_counts,
        "routing_health": {
            "unknown_predicted_intents": unknown_predicted_intents,
            "unknown_predicted_intent_count": len(unknown_predicted_intents),
            "fallback_confidence_below": fallback_threshold,
            "rows_forced_to_fallback_due_to_unknown_intent": operating_counts["fallback_unknown_intent"],
            "rows_forced_to_fallback_due_to_low_confidence": operating_counts["fallback_insufficient_confidence"],
        },
        "distribution": distributions,
        "confusion_matrices": {
            "persona": persona_confusion,
            "intent": intent_confusion,
            "route_tier": route_tier_confusion,
        },
        "top_persona_confusions": persona_confusions,
        "top_intent_confusions": intent_confusions,
        "highest_confidence_wrong_predictions": highest_confidence_serializable,
        "acceptance": evaluate_thresholds(
            {
                "persona_accuracy": persona_accuracy,
                "intent_accuracy": intent_accuracy,
                "joint_accuracy": joint_accuracy,
                "route_tier_accuracy": route_tier_accuracy,
                "short_circuit_precision": short_circuit_precision,
            }
        ),
        "label_refinement_candidates": label_refinement_candidates,
        "recommendations": recommendations,
    }

    errors = [row for row in matched_rows if row["error_types"]]
    errors.sort(key=lambda row: (-float(row["predicted_confidence"]), str(row["row_id"])))

    summary_path = output_dir / "evaluation_summary.json"
    report_path = output_dir / "evaluation_report.md"
    dashboard_path = output_dir / "evaluation_dashboard.html"
    errors_path = output_dir / "prediction_errors.csv"
    enriched_matches_path = output_dir / "matched_predictions_enriched.csv"
    confidence_summary_path = output_dir / "confidence_band_summary.csv"
    persona_slice_path = output_dir / "persona_accuracy_by_slice.csv"
    intent_slice_path = output_dir / "intent_accuracy_by_slice.csv"
    top_persona_confusions_path = output_dir / "top_persona_confusions.csv"
    top_confusions_path = output_dir / "top_intent_confusions.csv"
    persona_confusion_path = output_dir / "persona_confusion_matrix.csv"
    intent_confusion_path = output_dir / "intent_confusion_matrix.csv"
    route_confusion_path = output_dir / "route_tier_confusion_matrix.csv"
    error_fieldnames = [
        "row_id",
        "query",
        "gold_persona",
        "predicted_persona",
        "gold_intent",
        "predicted_intent",
        "gold_route_tier",
        "predicted_route_tier",
        "gold_short_circuit",
        "predicted_short_circuit",
        "predicted_confidence",
        "join_method",
        "predicted_intent_known",
        "fallback_due_to_confidence",
        "fallback_due_to_unknown_intent",
        "model",
        "latency_ms",
        "total_tokens",
        "estimated_cost_usd",
        "error_types",
    ]

    write_json(summary_path, summary)
    report_path.write_text(render_markdown_report(summary), encoding="utf-8")
    dashboard_path.write_text(render_html_report(summary), encoding="utf-8")
    write_csv(
        errors_path,
        error_fieldnames,
        [{field: row.get(field, "") for field in error_fieldnames} for row in errors],
    )
    write_csv(
        enriched_matches_path,
        [
            "row_id",
            "query",
            "gold_persona",
            "predicted_persona",
            "gold_intent",
            "predicted_intent",
            "gold_route_tier",
            "predicted_route_tier",
            "gold_short_circuit",
            "predicted_short_circuit",
            "predicted_confidence",
            "join_method",
            "predicted_intent_known",
            "fallback_due_to_confidence",
            "fallback_due_to_unknown_intent",
            "model",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "persona_correct",
            "intent_correct",
            "joint_correct",
            "route_tier_correct",
            "short_circuit_correct",
            "error_types",
        ],
        [
            {
                key: row.get(key, "")
                for key in [
                    "row_id",
                    "query",
                    "gold_persona",
                    "predicted_persona",
                    "gold_intent",
                    "predicted_intent",
                    "gold_route_tier",
                    "predicted_route_tier",
                    "gold_short_circuit",
                    "predicted_short_circuit",
                    "predicted_confidence",
                    "join_method",
                    "predicted_intent_known",
                    "fallback_due_to_confidence",
                    "fallback_due_to_unknown_intent",
                    "model",
                    "latency_ms",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "estimated_cost_usd",
                    "persona_correct",
                    "intent_correct",
                    "joint_correct",
                    "route_tier_correct",
                    "short_circuit_correct",
                    "error_types",
                ]
            }
            for row in matched_rows
        ],
    )
    write_csv(
        confidence_summary_path,
        ["confidence_band", "count", "coverage", "persona_accuracy", "intent_accuracy", "joint_accuracy", "route_tier_accuracy"],
        [
            {"confidence_band": band, **confidence_summary[band]}
            for band in CONFIDENCE_BAND_LABELS
        ],
    )
    write_csv(
        persona_slice_path,
        ["persona", "count", "accuracy"],
        [{"persona": name, **stats} for name, stats in sort_accuracy_map(per_persona_accuracy)],
    )
    write_csv(
        intent_slice_path,
        ["intent", "count", "accuracy"],
        [{"intent": name, **stats} for name, stats in sort_accuracy_map(per_intent_accuracy)],
    )
    write_csv(
        top_persona_confusions_path,
        ["gold", "predicted", "count", "row_rate"],
        persona_confusions,
    )
    write_csv(
        top_confusions_path,
        ["gold", "predicted", "count", "row_rate"],
        intent_confusions,
    )
    persona_headers, persona_rows = confusion_matrix_rows(persona_confusion)
    write_csv(
        persona_confusion_path,
        persona_headers,
        [dict(zip(persona_headers, row)) for row in persona_rows],
    )
    intent_headers, intent_rows = confusion_matrix_rows(intent_confusion)
    write_csv(
        intent_confusion_path,
        intent_headers,
        [dict(zip(intent_headers, row)) for row in intent_rows],
    )
    route_headers, route_rows = confusion_matrix_rows(route_tier_confusion)
    write_csv(
        route_confusion_path,
        route_headers,
        [dict(zip(route_headers, row)) for row in route_rows],
    )

    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {dashboard_path}")
    print(f"Wrote {errors_path}")
    print(f"Wrote {enriched_matches_path}")
    print(f"Wrote {top_persona_confusions_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate router/classifier predictions against hand labels."
    )
    parser.add_argument("--labels", required=True, help="Path to the labels CSV.")
    parser.add_argument("--predictions", required=True, help="Path to the predictions CSV.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated reports.")
    return parser.parse_args()


def normalized(value: str | None) -> str:
    return (value or "").strip()


def parse_bool(value: str | None) -> bool | None:
    text = normalized(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_float(value: str | None) -> float | None:
    text = normalized(value)
    if not text:
        return None
    return float(text)


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    if lower_index == upper_index:
        return lower_value
    weight = position - lower_index
    return lower_value + (upper_value - lower_value) * weight


def join_key(row: dict[str, str]) -> str:
    row_id = normalized(row.get("row_id"))
    if row_id:
        return f"row_id:{row_id}"
    query = normalized(row.get("query") or row.get("Query"))
    if query:
        return f"query:{query.lower()}"
    raise ValueError("Each row must include either row_id or query.")


def resolve_gold_route(row: dict[str, str]) -> str:
    for key in ("gold_route", "seed_route", "Route"):
        value = normalized(row.get(key))
        if value:
            return value
    raise ValueError(f"Could not resolve gold route for row: {row}")


def resolve_gold_short_circuit(row: dict[str, str], gold_route: str) -> bool:
    explicit = parse_bool(row.get("gold_short_circuit"))
    if explicit is not None:
        return explicit
    complexity = normalized(row.get("seed_complexity") or row.get("Complexity")).lower()
    if complexity:
        return complexity == "short_circuit"
    return gold_route == "short_circuit"


def resolve_predicted_route(row: dict[str, str]) -> str:
    for key in ("predicted_route", "route"):
        value = normalized(row.get(key))
        if value:
            return value
    raise ValueError(f"Could not resolve predicted route for row: {row}")


def resolve_predicted_short_circuit(row: dict[str, str], predicted_route: str) -> bool:
    explicit = parse_bool(row.get("predicted_short_circuit"))
    if explicit is not None:
        return explicit
    routing_path = normalized(row.get("routing_path")).lower()
    if routing_path:
        return routing_path == "short_circuit"
    return predicted_route == "short_circuit"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_num(value: float) -> str:
    return f"{value:.2f}"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in headers)
    body_rows = []
    for row in rows:
        body_cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        body_rows.append(f"<tr>{body_cells}</tr>")
    return (
        "<table>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def main() -> None:
    args = parse_args()
    labels_path = Path(args.labels)
    predictions_path = Path(args.predictions)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    label_rows = load_csv(labels_path)
    prediction_rows = load_csv(predictions_path)

    predictions_by_key = {join_key(row): row for row in prediction_rows}

    matched_rows: list[dict[str, object]] = []
    missing_predictions: list[dict[str, str]] = []
    for label_row in label_rows:
        key = join_key(label_row)
        prediction_row = predictions_by_key.get(key)
        if prediction_row is None:
            missing_predictions.append(label_row)
            continue

        gold_route = resolve_gold_route(label_row)
        predicted_route = resolve_predicted_route(prediction_row)
        gold_short_circuit = resolve_gold_short_circuit(label_row, gold_route)
        predicted_short_circuit = resolve_predicted_short_circuit(prediction_row, predicted_route)

        matched_rows.append(
            {
                "row_id": normalized(label_row.get("row_id")),
                "query": normalized(label_row.get("query") or label_row.get("Query")),
                "gold_route": gold_route,
                "predicted_route": predicted_route,
                "gold_short_circuit": gold_short_circuit,
                "predicted_short_circuit": predicted_short_circuit,
                "latency_ms": parse_float(prediction_row.get("latency_ms")),
                "prompt_tokens": parse_float(prediction_row.get("prompt_tokens")),
                "completion_tokens": parse_float(prediction_row.get("completion_tokens")),
                "total_tokens": parse_float(prediction_row.get("total_tokens")),
                "estimated_cost_usd": parse_float(prediction_row.get("estimated_cost_usd")),
                "routing_path": normalized(prediction_row.get("routing_path")),
                "model": normalized(prediction_row.get("model")),
            }
        )

    total_labels = len(label_rows)
    matched_count = len(matched_rows)
    missing_count = len(missing_predictions)

    correct_routes = sum(
        1 for row in matched_rows if row["gold_route"] == row["predicted_route"]
    )
    route_accuracy = safe_rate(correct_routes, matched_count)

    tp = sum(
        1
        for row in matched_rows
        if row["gold_short_circuit"] and row["predicted_short_circuit"]
    )
    tn = sum(
        1
        for row in matched_rows
        if not row["gold_short_circuit"] and not row["predicted_short_circuit"]
    )
    fp = sum(
        1
        for row in matched_rows
        if not row["gold_short_circuit"] and row["predicted_short_circuit"]
    )
    fn = sum(
        1
        for row in matched_rows
        if row["gold_short_circuit"] and not row["predicted_short_circuit"]
    )

    short_circuit_correct_rate = safe_rate(tp, tp + fn)
    short_circuit_precision = safe_rate(tp, tp + fp)
    short_circuit_boolean_accuracy = safe_rate(tp + tn, matched_count)

    latencies = [row["latency_ms"] for row in matched_rows if row["latency_ms"] is not None]
    total_tokens = [row["total_tokens"] for row in matched_rows if row["total_tokens"] is not None]
    prompt_tokens = [row["prompt_tokens"] for row in matched_rows if row["prompt_tokens"] is not None]
    completion_tokens = [row["completion_tokens"] for row in matched_rows if row["completion_tokens"] is not None]
    costs = [row["estimated_cost_usd"] for row in matched_rows if row["estimated_cost_usd"] is not None]

    gold_counts = Counter(str(row["gold_route"]) for row in matched_rows)
    predicted_counts = Counter(str(row["predicted_route"]) for row in matched_rows)
    routing_path_counts = Counter(
        str(row["routing_path"]) for row in matched_rows if row["routing_path"]
    )
    model_counts = Counter(str(row["model"]) for row in matched_rows if row["model"])

    routes = sorted(set(gold_counts) | set(predicted_counts))
    confusion_matrix: dict[str, dict[str, int]] = {
        gold_route: {predicted_route: 0 for predicted_route in routes}
        for gold_route in routes
    }
    for row in matched_rows:
        confusion_matrix[str(row["gold_route"])][str(row["predicted_route"])] += 1

    per_route_accuracy = {}
    for route in routes:
        route_total = gold_counts[route]
        route_correct = confusion_matrix[route].get(route, 0)
        per_route_accuracy[route] = {
            "count": route_total,
            "accuracy": safe_rate(route_correct, route_total),
        }

    summary = {
        "dataset": {
            "total_labels": total_labels,
            "matched_predictions": matched_count,
            "missing_predictions": missing_count,
        },
        "metrics": {
            "route_accuracy": route_accuracy,
            "short_circuit_correct_rate": short_circuit_correct_rate,
            "short_circuit_precision": short_circuit_precision,
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
            "avg": mean(latencies) if latencies else 0.0,
            "p50": median(latencies) if latencies else 0.0,
            "p95": quantile(latencies, 0.95) if latencies else 0.0,
            "max": max(latencies) if latencies else 0.0,
        },
        "tokens": {
            "avg_total_tokens": mean(total_tokens) if total_tokens else 0.0,
            "avg_prompt_tokens": mean(prompt_tokens) if prompt_tokens else 0.0,
            "avg_completion_tokens": mean(completion_tokens) if completion_tokens else 0.0,
            "total_tokens": sum(total_tokens) if total_tokens else 0.0,
        },
        "cost_usd": {
            "total": sum(costs) if costs else 0.0,
            "avg": mean(costs) if costs else 0.0,
        },
        "distribution": {
            "gold_routes": dict(sorted(gold_counts.items())),
            "predicted_routes": dict(sorted(predicted_counts.items())),
            "routing_paths": dict(sorted(routing_path_counts.items())),
            "models": dict(sorted(model_counts.items())),
            "per_route_accuracy": per_route_accuracy,
        },
        "confusion_matrix": confusion_matrix,
        "missing_prediction_queries": [
            normalized(row.get("query") or row.get("Query")) for row in missing_predictions
        ],
    }

    summary_path = output_dir / "evaluation_summary.json"
    report_path = output_dir / "evaluation_report.md"
    dashboard_path = output_dir / "evaluation_dashboard.html"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    route_rows = [
        [route, str(per_route_accuracy[route]["count"]), format_pct(per_route_accuracy[route]["accuracy"])]
        for route in routes
    ]
    confusion_rows = [
        [gold_route] + [str(confusion_matrix[gold_route][predicted_route]) for predicted_route in routes]
        for gold_route in routes
    ]
    path_rows = [[path, str(count)] for path, count in sorted(routing_path_counts.items())]

    markdown_report = "\n".join(
        [
            "# Phase 7 Evaluation Report",
            "",
            "## Dataset Coverage",
            f"- Labels: {total_labels}",
            f"- Matched predictions: {matched_count}",
            f"- Missing predictions: {missing_count}",
            "",
            "## Core Metrics",
            f"- Route accuracy: {format_pct(route_accuracy)}",
            f"- Correct short-circuit rate: {format_pct(short_circuit_correct_rate)}",
            f"- Short-circuit precision: {format_pct(short_circuit_precision)}",
            f"- Short-circuit boolean accuracy: {format_pct(short_circuit_boolean_accuracy)}",
            "",
            "## Latency",
            f"- Average latency: {format_num(summary['latency_ms']['avg'])} ms",
            f"- P50 latency: {format_num(summary['latency_ms']['p50'])} ms",
            f"- P95 latency: {format_num(summary['latency_ms']['p95'])} ms",
            f"- Max latency: {format_num(summary['latency_ms']['max'])} ms",
            "",
            "## Tokens And Cost",
            f"- Average total tokens: {format_num(summary['tokens']['avg_total_tokens'])}",
            f"- Total tokens: {format_num(summary['tokens']['total_tokens'])}",
            f"- Total cost: ${summary['cost_usd']['total']:.4f}",
            f"- Average cost per query: ${summary['cost_usd']['avg']:.6f}",
            "",
            "## Route Accuracy By Gold Route",
            "| Route | Count | Accuracy |",
            "| --- | ---: | ---: |",
            *[
                f"| {route} | {per_route_accuracy[route]['count']} | {format_pct(per_route_accuracy[route]['accuracy'])} |"
                for route in routes
            ],
            "",
            "## Routing Path Distribution",
            "| Routing Path | Count |",
            "| --- | ---: |",
            *[f"| {path} | {count} |" for path, count in sorted(routing_path_counts.items())],
            "",
            "## Confusion Matrix",
            "| Gold \\ Predicted | " + " | ".join(routes) + " |",
            "| --- | " + " | ".join(["---:"] * len(routes)) + " |",
            *[
                "| " + gold_route + " | " + " | ".join(
                    str(confusion_matrix[gold_route][predicted_route]) for predicted_route in routes
                ) + " |"
                for gold_route in routes
            ],
        ]
    )
    report_path.write_text(markdown_report + "\n", encoding="utf-8")

    metric_cards = "".join(
        [
            f"<section class='card'><h2>Route accuracy</h2><p>{format_pct(route_accuracy)}</p></section>",
            f"<section class='card'><h2>Short-circuit correct rate</h2><p>{format_pct(short_circuit_correct_rate)}</p></section>",
            f"<section class='card'><h2>P95 latency</h2><p>{format_num(summary['latency_ms']['p95'])} ms</p></section>",
            f"<section class='card'><h2>Total cost</h2><p>${summary['cost_usd']['total']:.4f}</p></section>",
        ]
    )

    dashboard_html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Phase 7 Evaluation Dashboard</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --panel: #fffaf2;
      --ink: #1f2933;
      --muted: #5f6c7b;
      --accent: #b85c38;
      --line: #e5d7c6;
      --good: #1d6f42;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Georgia, 'Times New Roman', serif; background: linear-gradient(180deg, #efe5d6 0%, var(--bg) 50%, #f7f2ea 100%); color: var(--ink); }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 2.4rem; letter-spacing: 0.02em; }}
    p.lede {{ max-width: 760px; color: var(--muted); font-size: 1.05rem; line-height: 1.6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 24px 0 28px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; box-shadow: 0 12px 30px rgba(73, 50, 24, 0.08); }}
    .card p {{ font-size: 2rem; margin: 0; color: var(--accent); }}
    .section {{ margin-top: 24px; background: rgba(255, 250, 242, 0.82); border: 1px solid var(--line); border-radius: 20px; padding: 20px; backdrop-filter: blur(4px); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.96rem; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    thead th {{ color: var(--muted); font-weight: 600; }}
    .muted {{ color: var(--muted); }}
    .good {{ color: var(--good); }}
    @media (max-width: 720px) {{
      h1 {{ font-size: 1.9rem; }}
      .card p {{ font-size: 1.7rem; }}
      th, td {{ padding: 8px 10px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Phase 7 Evaluation Dashboard</h1>
    <p class=\"lede\">This report measures route accuracy, short-circuit behavior, latency, tokens, and cost for the current classifier export. Use it as the lightweight decision surface for whether the router is ready to promote.</p>
    <div class=\"grid\">{metric_cards}</div>
    <section class=\"section\">
      <h2>Coverage</h2>
      <p class=\"muted\">Matched {matched_count} of {total_labels} labeled queries. Missing predictions: {missing_count}.</p>
    </section>
    <section class=\"section\">
      <h2>Latency And Cost</h2>
      {render_table(
          ["Metric", "Value"],
          [
              ["Average latency", f"{format_num(summary['latency_ms']['avg'])} ms"],
              ["P50 latency", f"{format_num(summary['latency_ms']['p50'])} ms"],
              ["P95 latency", f"{format_num(summary['latency_ms']['p95'])} ms"],
              ["Max latency", f"{format_num(summary['latency_ms']['max'])} ms"],
              ["Average total tokens", format_num(summary['tokens']['avg_total_tokens'])],
              ["Total tokens", format_num(summary['tokens']['total_tokens'])],
              ["Total cost", f"${summary['cost_usd']['total']:.4f}"],
              ["Average cost per query", f"${summary['cost_usd']['avg']:.6f}"],
          ],
      )}
    </section>
    <section class=\"section\">
      <h2>Per-Route Accuracy</h2>
      {render_table(["Route", "Count", "Accuracy"], route_rows)}
    </section>
    <section class=\"section\">
      <h2>Routing Path Distribution</h2>
      {render_table(["Routing path", "Count"], path_rows or [["No routing path data", "0"]])}
    </section>
    <section class=\"section\">
      <h2>Confusion Matrix</h2>
      {render_table(["Gold \\ Predicted"] + routes, confusion_rows)}
    </section>
  </main>
</body>
</html>
"""
    dashboard_path.write_text(dashboard_html, encoding="utf-8")

    print(f"Wrote summary to {summary_path}")
    print(f"Wrote markdown report to {report_path}")
    print(f"Wrote dashboard to {dashboard_path}")


if __name__ == "__main__":
    main()
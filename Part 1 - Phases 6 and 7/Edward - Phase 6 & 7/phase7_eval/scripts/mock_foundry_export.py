from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


OUTPUT_COLUMNS = [
    "row_id",
    "query",
    "predicted_route",
    "predicted_short_circuit",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "routing_path",
    "model",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a mock Foundry export to validate the evaluation pipeline."
    )
    parser.add_argument("--labels", required=True, help="Path to the hand-label or source CSV.")
    parser.add_argument("--output", required=True, help="Path to the output predictions CSV.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility.")
    return parser.parse_args()


def normalized(value: str | None) -> str:
    return (value or "").strip()


def resolve_gold_route(row: dict[str, str]) -> str:
    for key in ("gold_route", "seed_route", "Route"):
        value = normalized(row.get(key))
        if value:
            return value
    raise ValueError("Could not resolve a route from the labels file.")


def resolve_gold_short_circuit(row: dict[str, str], gold_route: str) -> bool:
    explicit = normalized(row.get("gold_short_circuit")).lower()
    if explicit in {"true", "1", "yes", "y"}:
        return True
    if explicit in {"false", "0", "no", "n"}:
        return False
    complexity = normalized(row.get("seed_complexity") or row.get("Complexity")).lower()
    if complexity:
        return complexity == "short_circuit"
    return gold_route == "short_circuit"


def route_catalog(rows: list[dict[str, str]]) -> list[str]:
    routes = sorted({resolve_gold_route(row) for row in rows})
    if not routes:
        raise ValueError("No routes found in the labels file.")
    return routes


def accuracy_for_row(row: dict[str, str]) -> float:
    complexity = normalized(row.get("seed_complexity") or row.get("Complexity"))
    if complexity == "short_circuit":
        return 0.96
    if complexity == "medium":
        return 0.9
    if complexity == "complex":
        return 0.82
    if complexity == "llm_needed":
        return 0.74
    return 0.88


def generate_prediction(
    row: dict[str, str], routes: list[str], rng: random.Random
) -> dict[str, str]:
    gold_route = resolve_gold_route(row)
    gold_short_circuit = resolve_gold_short_circuit(row, gold_route)
    use_gold = rng.random() < accuracy_for_row(row)
    alternative_routes = [route for route in routes if route != gold_route]
    predicted_route = gold_route if use_gold or not alternative_routes else rng.choice(alternative_routes)

    if gold_short_circuit:
        predicted_short_circuit = rng.random() < 0.92
    else:
        predicted_short_circuit = rng.random() < 0.04

    latency_floor = 80 if predicted_short_circuit else 550
    latency_span = 180 if predicted_short_circuit else 1350
    latency_ms = latency_floor + rng.randint(0, latency_span)

    prompt_tokens = rng.randint(18, 45) if predicted_short_circuit else rng.randint(140, 420)
    completion_tokens = rng.randint(2, 18) if predicted_short_circuit else rng.randint(20, 120)
    total_tokens = prompt_tokens + completion_tokens
    estimated_cost_usd = round(prompt_tokens * 0.000001 + completion_tokens * 0.000002, 6)
    routing_path = "short_circuit" if predicted_short_circuit else f"llm:{predicted_route}"
    model = "heuristic-router" if predicted_short_circuit else "gpt-4.1-mini"

    return {
        "row_id": normalized(row.get("row_id")),
        "query": normalized(row.get("query") or row.get("Query")),
        "predicted_route": predicted_route,
        "predicted_short_circuit": str(predicted_short_circuit).lower(),
        "latency_ms": str(latency_ms),
        "prompt_tokens": str(prompt_tokens),
        "completion_tokens": str(completion_tokens),
        "total_tokens": str(total_tokens),
        "estimated_cost_usd": f"{estimated_cost_usd:.6f}",
        "routing_path": routing_path,
        "model": model,
    }


def main() -> None:
    args = parse_args()
    labels_path = Path(args.labels)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with labels_path.open("r", encoding="utf-8-sig", newline="") as labels_file:
        rows = list(csv.DictReader(labels_file))

    routes = route_catalog(rows)
    rng = random.Random(args.seed)
    predictions = [generate_prediction(row, routes, rng) for row in rows]

    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(predictions)

    print(f"Wrote {len(predictions)} mock predictions to {output_path}")


if __name__ == "__main__":
    main()
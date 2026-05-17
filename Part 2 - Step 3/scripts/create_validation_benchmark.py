from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from step3_validation.common import (  # noqa: E402
    derive_route_tier,
    derive_short_circuit,
    entities_text_to_json,
    load_csv,
    load_route_config,
    normalized,
    query_sha1,
    require_columns,
    safe_rate,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a fixed held-out benchmark for step 3 validation."
    )
    parser.add_argument("--source", required=True, help="Path to the cleaned dataset CSV.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for benchmark outputs.",
    )
    parser.add_argument(
        "--benchmark-size",
        type=int,
        default=200,
        help="Number of held-out queries to select. Default: 200.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling.",
    )
    parser.add_argument(
        "--route-config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "intent_to_route_tier.json"),
        help="Path to the intent-to-route-tier mapping JSON.",
    )
    return parser.parse_args()


def proportional_allocation(counts: dict[str, int], total_size: int) -> dict[str, int]:
    if total_size <= 0:
        raise ValueError("Benchmark size must be positive.")
    intents = sorted(counts)
    if total_size < len(intents):
        raise ValueError(
            f"Benchmark size {total_size} is smaller than the number of intents {len(intents)}."
        )

    total_rows = sum(counts.values())
    allocation = {intent: 1 for intent in intents}
    remaining = total_size - len(intents)
    if remaining == 0:
        return allocation

    raw_targets = {}
    for intent in intents:
        raw = counts[intent] / total_rows * total_size
        raw_targets[intent] = raw

    remainders = []
    for intent in intents:
        extra = max(0, int(raw_targets[intent]) - 1)
        extra = min(extra, counts[intent] - allocation[intent])
        allocation[intent] += extra
        remaining -= extra
        remainders.append((raw_targets[intent] - int(raw_targets[intent]), intent))

    while remaining > 0:
        made_progress = False
        for _, intent in sorted(remainders, reverse=True):
            if allocation[intent] < counts[intent]:
                allocation[intent] += 1
                remaining -= 1
                made_progress = True
                if remaining == 0:
                    break
        if not made_progress:
            break
    return allocation


def select_rows_for_intent(rows: list[dict[str, object]], quota: int, rng: random.Random) -> list[dict[str, object]]:
    by_persona: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_persona[str(row["persona"])].append(row)

    personas = sorted(by_persona)
    for persona in personas:
        rng.shuffle(by_persona[persona])

    selected: list[dict[str, object]] = []
    while len(selected) < quota:
        made_progress = False
        for persona in personas:
            bucket = by_persona[persona]
            if bucket:
                selected.append(bucket.pop())
                made_progress = True
                if len(selected) == quota:
                    break
        if not made_progress:
            break

    return selected


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    route_config = load_route_config(Path(args.route_config))
    rng = random.Random(args.seed)

    source_rows = load_csv(source_path)
    if not source_rows:
        raise ValueError("Source dataset is empty.")

    resolved = require_columns(
        list(source_rows[0].keys()),
        {
            "query": ["Query", "query"],
            "persona": ["Persona", "persona"],
            "intent": ["Intent", "intent"],
        },
    )
    entities_column = ""
    for candidate in ("Entities", "entities", "gold_entities_json"):
        if candidate in source_rows[0]:
            entities_column = candidate
            break

    normalized_rows: list[dict[str, object]] = []
    for index, row in enumerate(source_rows, start=1):
        query = normalized(str(row[resolved["query"]]))
        persona = normalized(str(row[resolved["persona"]]))
        intent = normalized(str(row[resolved["intent"]]))
        if not query or not persona or not intent:
            continue
        normalized_rows.append(
            {
                "source_row_number": index,
                "query": query,
                "persona": persona,
                "intent": intent,
                "entities_json": entities_text_to_json(row.get(entities_column)) if entities_column else "[]",
            }
        )

    rows_by_query: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in normalized_rows:
        rows_by_query[str(row["query"]).lower()].append(row)

    deduped_rows: list[dict[str, object]] = []
    duplicate_same_label_rows_dropped = 0
    conflicting_query_groups_excluded = 0
    conflicting_query_rows_excluded = 0
    conflicting_query_preview: list[dict[str, object]] = []
    for query_key, grouped_rows in rows_by_query.items():
        label_signatures = {
            (str(row["persona"]), str(row["intent"]))
            for row in grouped_rows
        }
        if len(label_signatures) > 1:
            conflicting_query_groups_excluded += 1
            conflicting_query_rows_excluded += len(grouped_rows)
            if len(conflicting_query_preview) < 10:
                conflicting_query_preview.append(
                    {
                        "query": grouped_rows[0]["query"],
                        "rows": len(grouped_rows),
                        "label_signatures": sorted(
                            [{"persona": persona, "intent": intent} for persona, intent in label_signatures],
                            key=lambda item: (item["persona"], item["intent"]),
                        ),
                    }
                )
            continue
        deduped_rows.append(grouped_rows[0])
        duplicate_same_label_rows_dropped += len(grouped_rows) - 1

    benchmark_pool_rows = len(deduped_rows)
    if benchmark_pool_rows < args.benchmark_size:
        raise ValueError(
            "Benchmark size "
            f"{args.benchmark_size} is larger than the unique, non-conflicting benchmark pool {benchmark_pool_rows}."
        )

    by_intent: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in deduped_rows:
        by_intent[str(row["intent"])].append(row)

    counts = {intent: len(rows) for intent, rows in by_intent.items()}
    allocation = proportional_allocation(counts, args.benchmark_size)

    selected_rows: list[dict[str, object]] = []
    for intent, rows in sorted(by_intent.items()):
        selected_rows.extend(select_rows_for_intent(rows, allocation[intent], rng))

    selected_rows = sorted(selected_rows, key=lambda row: (str(row["intent"]), str(row["persona"]), str(row["query"])))
    if len(selected_rows) != args.benchmark_size:
        raise RuntimeError(
            f"Expected {args.benchmark_size} benchmark rows but selected {len(selected_rows)}."
        )

    benchmark_rows = []
    exclusion_rows = []
    for index, row in enumerate(selected_rows, start=1):
        row_id = f"step3_{index:04d}"
        route_tier = derive_route_tier(
            intent=str(row["intent"]),
            confidence=None,
            config=route_config,
            apply_confidence_fallback=False,
        )
        benchmark_rows.append(
            {
                "row_id": row_id,
                "source_row_number": row["source_row_number"],
                "source_query_sha1": query_sha1(str(row["query"])),
                "query": row["query"],
                "gold_persona": row["persona"],
                "gold_intent": row["intent"],
                "gold_entities_json": row["entities_json"],
                "gold_route_tier": route_tier,
                "gold_short_circuit": str(derive_short_circuit(route_tier)).lower(),
                "label_status": "todo",
                "reviewer_notes": "",
            }
        )
        exclusion_rows.append(
            {
                "row_id": row_id,
                "source_row_number": row["source_row_number"],
                "source_query_sha1": query_sha1(str(row["query"])),
                "query": row["query"],
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_path = output_dir / "benchmark_gold.csv"
    review_template_path = output_dir / "benchmark_review_template.csv"
    exclusion_path = output_dir / "benchmark_exclusion_manifest.csv"
    summary_path = output_dir / "benchmark_summary.json"

    write_csv(
        benchmark_path,
        [
            "row_id",
            "source_row_number",
            "source_query_sha1",
            "query",
            "gold_persona",
            "gold_intent",
            "gold_entities_json",
            "gold_route_tier",
            "gold_short_circuit",
            "label_status",
            "reviewer_notes",
        ],
        benchmark_rows,
    )
    write_csv(
        review_template_path,
        [
            "row_id",
            "source_row_number",
            "source_query_sha1",
            "query",
            "gold_persona",
            "gold_intent",
            "gold_entities_json",
            "gold_route_tier",
            "gold_short_circuit",
            "label_status",
            "reviewer_notes",
        ],
        benchmark_rows,
    )
    write_csv(
        exclusion_path,
        ["row_id", "source_row_number", "source_query_sha1", "query"],
        exclusion_rows,
    )

    persona_counts: dict[str, int] = defaultdict(int)
    intent_counts: dict[str, int] = defaultdict(int)
    route_counts: dict[str, int] = defaultdict(int)
    for row in benchmark_rows:
        persona_counts[str(row["gold_persona"])] += 1
        intent_counts[str(row["gold_intent"])] += 1
        route_counts[str(row["gold_route_tier"])] += 1

    summary = {
        "raw_source_rows": len(source_rows),
        "usable_source_rows": len(normalized_rows),
        "unique_query_groups": len(rows_by_query),
        "duplicate_same_label_query_rows_dropped": duplicate_same_label_rows_dropped,
        "conflicting_query_groups_excluded": conflicting_query_groups_excluded,
        "conflicting_query_rows_excluded": conflicting_query_rows_excluded,
        "benchmark_pool_rows": benchmark_pool_rows,
        "benchmark_size": len(benchmark_rows),
        "seed": args.seed,
        "intent_allocation": allocation,
        "intent_coverage": intent_counts,
        "persona_coverage": persona_counts,
        "route_tier_coverage": route_counts,
        "benchmark_size_ratio": safe_rate(len(benchmark_rows), benchmark_pool_rows),
        "selection_policy": {
            "intent_sampling": "proportional_with_minimum_one_per_intent",
            "persona_sampling_within_intent": "round_robin_after_shuffle",
            "duplicate_query_handling": "drop_exact-query duplicates with same label; exclude exact-query conflicts with different labels",
        },
        "conflicting_query_preview": conflicting_query_preview,
        "files": {
            "benchmark_gold": str(benchmark_path),
            "benchmark_review_template": str(review_template_path),
            "benchmark_exclusion_manifest": str(exclusion_path),
        },
    }
    write_json(summary_path, summary)
    print(f"Wrote benchmark to {benchmark_path}")
    print(f"Wrote review template to {review_template_path}")
    print(f"Wrote exclusion manifest to {exclusion_path}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()

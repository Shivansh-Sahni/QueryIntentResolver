from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from step3_validation.common import (  # noqa: E402
    load_csv,
    normalized,
    require_columns,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a mock prediction export for step 3 dry-run validation."
    )
    parser.add_argument("--labels", required=True, help="Path to benchmark_gold.csv.")
    parser.add_argument("--output", required=True, help="Path to write the prediction CSV.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--persona-accuracy-target",
        type=float,
        default=0.88,
        help="Approximate persona accuracy target for the simulation.",
    )
    parser.add_argument(
        "--intent-accuracy-target",
        type=float,
        default=0.92,
        help="Approximate intent accuracy target for the simulation.",
    )
    return parser.parse_args()


def choose_wrong_label(labels: list[str], gold: str, rng: random.Random) -> str:
    candidates = [label for label in labels if label != gold]
    if not candidates:
        return gold
    return rng.choice(candidates)


def build_entity_prediction(gold_entities_json: str, rng: random.Random) -> str:
    if rng.random() < 0.85:
        return gold_entities_json
    try:
        payload = json.loads(gold_entities_json)
        if isinstance(payload, list) and payload:
            return json.dumps(payload[:-1] or payload)
    except json.JSONDecodeError:
        pass
    return "[]"


def main() -> None:
    args = parse_args()
    labels_path = Path(args.labels)
    output_path = Path(args.output)
    rng = random.Random(args.seed)

    label_rows = load_csv(labels_path)
    if not label_rows:
        raise ValueError("Labels file is empty.")

    resolved = require_columns(
        list(label_rows[0].keys()),
        {
            "row_id": ["row_id"],
            "query": ["query", "Query"],
            "gold_persona": ["gold_persona", "Persona"],
            "gold_intent": ["gold_intent", "Intent"],
        },
    )

    personas = sorted(
        {normalized(row[resolved["gold_persona"]]) for row in label_rows if normalized(row[resolved["gold_persona"]])}
    )
    intents = sorted(
        {normalized(row[resolved["gold_intent"]]) for row in label_rows if normalized(row[resolved["gold_intent"]])}
    )

    intent_groups: dict[str, list[str]] = defaultdict(list)
    for intent in intents:
        if intent in {"exact_lookup", "attribute_lookup"}:
            intent_groups["short_circuit"].append(intent)
        elif intent in {"filtered_search"}:
            intent_groups["standard_search"].append(intent)
        else:
            intent_groups["agentic"].append(intent)

    prediction_rows = []
    for row in label_rows:
        gold_persona = normalized(row[resolved["gold_persona"]])
        gold_intent = normalized(row[resolved["gold_intent"]])

        predicted_persona = gold_persona
        predicted_intent = gold_intent

        if rng.random() > args.persona_accuracy_target:
            predicted_persona = choose_wrong_label(personas, gold_persona, rng)

        if rng.random() > args.intent_accuracy_target:
            if gold_intent in intent_groups["short_circuit"]:
                pool = intent_groups["short_circuit"] + intent_groups["standard_search"]
            elif gold_intent in intent_groups["standard_search"]:
                pool = intent_groups["short_circuit"] + intent_groups["agentic"]
            else:
                pool = intent_groups["agentic"] + intent_groups["standard_search"]
            predicted_intent = choose_wrong_label(sorted(set(pool)), gold_intent, rng)

        joint_correct = predicted_persona == gold_persona and predicted_intent == gold_intent
        if joint_correct:
            confidence = round(rng.uniform(0.81, 0.98), 3)
        elif predicted_intent == gold_intent or predicted_persona == gold_persona:
            confidence = round(rng.uniform(0.58, 0.84), 3)
        else:
            confidence = round(rng.uniform(0.28, 0.72), 3)

        prompt_tokens = rng.randint(150, 260)
        completion_tokens = rng.randint(25, 75)
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = rng.randint(450, 1650)
        estimated_cost = round(total_tokens * 0.0000012, 6)
        model = "unsloth-step2-v1-escalated" if confidence < 0.65 else "unsloth-step2-v1"

        prediction_rows.append(
            {
                "row_id": normalized(row[resolved["row_id"]]),
                "query": normalized(row[resolved["query"]]),
                "predicted_persona": predicted_persona,
                "predicted_intent": predicted_intent,
                "predicted_confidence": confidence,
                "predicted_entities_json": build_entity_prediction(normalized(row.get("gold_entities_json")), rng),
                "model": model,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": estimated_cost,
            }
        )

    write_csv(
        output_path,
        [
            "row_id",
            "query",
            "predicted_persona",
            "predicted_intent",
            "predicted_confidence",
            "predicted_entities_json",
            "model",
            "latency_ms",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
        ],
        prediction_rows,
    )
    print(f"Wrote mock predictions to {output_path}")


if __name__ == "__main__":
    main()

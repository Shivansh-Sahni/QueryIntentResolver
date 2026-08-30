from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

INTENT_TO_ROUTE = {
    "exact_lookup": "short_circuit",
    "attribute_lookup": "short_circuit",
    "filtered_search": "medium",
    "admissions_process": "medium",
    "career_outcomes": "medium",
    "cost_financial_aid": "medium",
    "b2b_partnership": "medium",
    "profile_management": "medium",
    "multi_constraint": "complex",
    "comparison": "complex",
    "recommendation": "complex",
    "strategy": "complex",
    "analytics_request": "complex",
    "rewrite_needed": "complex",
    "advisory": "llm_needed",
    "emotional_advisory": "llm_needed",
    "reflective_advisory": "llm_needed",
    "campus_life_fit": "llm_needed",
}


def slugify(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_query(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def find_col(frame: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {slugify(column): column for column in frame.columns}
    for name in names:
        key = slugify(name)
        if key in lookup:
            return lookup[key]
    return None


def parse_intent(value: object) -> str:
    text = str(value or "")
    match = re.search(r"intent\s*[:=]\s*([a-zA-Z0-9_\- ]+)", text, flags=re.IGNORECASE)
    if match:
        return slugify(match.group(1).splitlines()[0])
    return slugify(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt a Qwen persona/intent export to the frozen V1 route contract")
    parser.add_argument("--benchmark-input", type=Path, required=True)
    parser.add_argument("--qwen-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unknown-intent-route", default="llm_needed")
    args = parser.parse_args()

    benchmark = pd.read_csv(args.benchmark_input, dtype=str, keep_default_na=False)
    raw = pd.read_csv(args.qwen_export, dtype=str, keep_default_na=False)
    if {"benchmark_id", "query_text"} - set(benchmark.columns):
        raise ValueError("Benchmark input must contain benchmark_id and query_text")

    id_col = find_col(raw, ["benchmark_id", "benchmark_row_id", "row_id", "id"])
    query_col = find_col(raw, ["query_text", "query", "input"])
    intent_col = find_col(raw, ["predicted_intent", "intent", "output", "response", "raw_response"])
    if intent_col is None:
        raise ValueError("Qwen export must include an intent or response column")

    if id_col:
        keyed = raw.rename(columns={id_col: "benchmark_id"}).copy()
        if keyed["benchmark_id"].duplicated().any():
            raise ValueError("Qwen export contains duplicate benchmark IDs")
        adapted = benchmark[["benchmark_id", "query_text"]].merge(
            keyed, on="benchmark_id", how="left", validate="one_to_one"
        )
    elif query_col:
        keyed = raw.copy()
        keyed["_query_norm"] = keyed[query_col].map(normalize_query)
        if keyed["_query_norm"].duplicated().any():
            raise ValueError("Qwen export contains duplicate queries; include benchmark_id instead")
        base = benchmark[["benchmark_id", "query_text"]].copy()
        base["_query_norm"] = base["query_text"].map(normalize_query)
        adapted = base.merge(keyed, on="_query_norm", how="left", validate="one_to_one")
    else:
        raise ValueError("Qwen export must include benchmark_id or query text")

    adapted["predicted_intent"] = adapted[intent_col].map(parse_intent)
    if adapted["predicted_intent"].eq("").any():
        raise ValueError(f"Qwen export is missing {int(adapted['predicted_intent'].eq('').sum())} predictions")
    adapted["predicted_route_raw"] = (
        adapted["predicted_intent"].map(INTENT_TO_ROUTE).fillna(args.unknown_intent_route)
    )

    confidence_col = find_col(adapted, ["confidence", "predicted_confidence", "score"])
    latency_col = find_col(adapted, ["latency_ms", "inference_latency_ms", "latency"])
    cost_col = find_col(adapted, ["estimated_cost_usd", "cost_usd", "cost"])
    adapted["confidence"] = (
        pd.to_numeric(adapted[confidence_col], errors="coerce").fillna(0.5).clip(0.0, 1.0)
        if confidence_col
        else 0.5
    )
    unknown = ~adapted["predicted_intent"].isin(INTENT_TO_ROUTE)
    adapted.loc[unknown, "confidence"] = adapted.loc[unknown, "confidence"].clip(upper=0.39)
    adapted["latency_ms"] = (
        pd.to_numeric(adapted[latency_col], errors="coerce").fillna(0.0) if latency_col else 0.0
    )
    adapted["estimated_cost_usd"] = (
        pd.to_numeric(adapted[cost_col], errors="coerce").fillna(0.0) if cost_col else 0.0
    )
    adapted["model"] = "anthony_qwen2_5_3b_lora_intent_to_route"

    columns = [
        "benchmark_id",
        "query_text",
        "predicted_route_raw",
        "confidence",
        "predicted_intent",
        "latency_ms",
        "estimated_cost_usd",
        "model",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    adapted[columns].to_csv(args.output, index=False)
    print(f"Wrote {len(adapted)} adapted Qwen predictions to {args.output}")


if __name__ == "__main__":
    main()

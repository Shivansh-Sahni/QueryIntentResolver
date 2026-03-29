"""
Inference helper for the revised Query Intent Resolver baseline.

Example:
python run_inference_example.py --model_dir outputs_revised --query "schools like Stanford but cheaper"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from resolver_utils import (
    ROUTE_MAP,
    TIER_MAP,
    apply_strict_rule_layer,
    confidence_from_pipeline,
    extract_entity_types,
    normalize_labeled_dataframe,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True, type=Path)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    persona_model = joblib.load(args.model_dir / "persona_model.joblib")
    intent_model = joblib.load(args.model_dir / "intent_model.joblib")

    df = pd.DataFrame({"query_text": [args.query]})
    df["pred_persona"] = persona_model.predict(df["query_text"])
    df["pred_intent"] = intent_model.predict(df["query_text"])
    df["persona_confidence"] = confidence_from_pipeline(persona_model, df["query_text"])
    df["intent_confidence"] = confidence_from_pipeline(intent_model, df["query_text"])

    ruled = apply_strict_rule_layer(df, query_col="query_text")
    if ruled.at[0, "rule_persona"]:
        df.at[0, "pred_persona"] = ruled.at[0, "rule_persona"]
    if ruled.at[0, "rule_intent"]:
        df.at[0, "pred_intent"] = ruled.at[0, "rule_intent"]

    normalized = normalize_labeled_dataframe(
        df[["query_text", "pred_persona", "pred_intent"]].rename(
            columns={
                "pred_persona": "persona",
                "pred_intent": "intent_label",
            }
        ),
        query_col="query_text",
        persona_col="persona",
        intent_col="intent_label",
        route_col="route",
        tier_col="tier",
    )
    df.at[0, "pred_persona"] = normalized.at[0, "persona"]
    df.at[0, "pred_intent"] = normalized.at[0, "intent_label"]

    intent_label = df.at[0, "pred_intent"]
    result = {
        "query_text": args.query,
        "persona": df.at[0, "pred_persona"],
        "intent_label": intent_label,
        "persona_confidence": round(float(df.at[0, "persona_confidence"]), 4),
        "intent_confidence": round(float(df.at[0, "intent_confidence"]), 4),
        "route": ROUTE_MAP.get(intent_label, "fallback"),
        "tier": TIER_MAP.get(intent_label, "fallback"),
        "entity_types": extract_entity_types(args.query),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

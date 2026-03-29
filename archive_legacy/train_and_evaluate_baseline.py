"""
Revised training and evaluation script for the Query Intent Resolver Phase 6/7 package.

What this script does
---------------------
1. Loads the raw training and gold evaluation CSVs.
2. Normalizes the label space so the artifacts match the route map.
3. Exports dataset breakdowns for intent/persona/entity balance review.
4. Compares multiple offline model families.
5. Saves the best mixed setup:
   - persona: TF-IDF + Multinomial Naive Bayes
   - intent: word+character TF-IDF + Logistic Regression
6. Applies a strict rule layer for only the safest shortcut cases.
7. Writes revised metrics, reports, predictions, normalized CSVs, and trained models.

Recommended usage
-----------------
python train_and_evaluate_baseline.py \
  --train training_dataset_4620_rows.csv \
  --eval evaluation_gold_300_queries.csv \
  --out_dir outputs_revised
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import joblib
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

from resolver_utils import (
    ROUTE_MAP,
    TIER_MAP,
    apply_strict_rule_layer,
    confidence_from_pipeline,
    normalize_labeled_dataframe,
)


ModelBuilder = Callable[[], Pipeline]


def load_train(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"query_text", "persona", "intent_label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Training file missing columns: {sorted(missing)}")
    return normalize_labeled_dataframe(
        df,
        query_col="query_text",
        persona_col="persona",
        intent_col="intent_label",
        route_col="route",
        tier_col="tier",
    )


def load_eval(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"query_text", "true_persona", "true_intent"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Eval file missing columns: {sorted(missing)}")
    return normalize_labeled_dataframe(
        df,
        query_col="query_text",
        persona_col="true_persona",
        intent_col="true_intent",
        route_col="expected_route",
        tier_col="expected_tier",
    )


def build_nb_model() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=20000,
                ),
            ),
            ("clf", MultinomialNB()),
        ]
    )


def build_lsa_logreg_model() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=30000,
                ),
            ),
            ("svd", TruncatedSVD(n_components=300, random_state=42)),
            (
                "clf",
                LogisticRegression(
                    max_iter=3000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def build_char_word_logreg_model() -> Pipeline:
    features = FeatureUnion(
        transformer_list=[
            (
                "word",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=25000,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                    min_df=2,
                    max_features=20000,
                ),
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("features", features),
            (
                "clf",
                LogisticRegression(
                    max_iter=3000,
                    class_weight="balanced",
                    solver="saga",
                    random_state=42,
                ),
            ),
        ]
    )


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def breakdown_from_series(series: pd.Series, *, label: str) -> pd.DataFrame:
    counts = series.value_counts().rename_axis(label).reset_index(name="count")
    counts["share"] = counts["count"] / counts["count"].sum()
    return counts


def breakdown_from_entity_types(series: pd.Series) -> pd.DataFrame:
    exploded = (
        series.fillna("")
        .str.split(",")
        .explode()
        .str.strip()
    )
    exploded = exploded[exploded != ""]
    return breakdown_from_series(exploded, label="entity_type")


def compute_metrics(predictions: pd.DataFrame) -> dict[str, object]:
    per_tier = {
        tier: {
            "count": int(mask.sum()),
            "route_accuracy": float((predictions.loc[mask, "expected_route"] == predictions.loc[mask, "pred_route"]).mean())
            if mask.any()
            else 0.0,
        }
        for tier in ["easy", "medium", "complex"]
        for mask in [predictions["expected_tier"] == tier]
    }

    confidence_bands: dict[str, dict[str, float]] = {}
    for lower, upper in [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]:
        label = f"{lower:.1f}-{upper:.1f}"
        band_mask = (predictions["intent_conf"] > lower) & (predictions["intent_conf"] <= upper)
        if lower == 0.0:
            band_mask = predictions["intent_conf"] <= upper
        confidence_bands[label] = {
            "count": int(band_mask.sum()),
            "intent_accuracy": float((predictions.loc[band_mask, "true_intent"] == predictions.loc[band_mask, "pred_intent"]).mean())
            if band_mask.any()
            else 0.0,
            "route_accuracy": float((predictions.loc[band_mask, "expected_route"] == predictions.loc[band_mask, "pred_route"]).mean())
            if band_mask.any()
            else 0.0,
        }

    easy_pred_mask = predictions["pred_tier"] == "easy"
    easy_gold_mask = predictions["expected_tier"] == "easy"

    return {
        "persona_accuracy": float(accuracy_score(predictions["true_persona"], predictions["pred_persona"])),
        "intent_accuracy": float(accuracy_score(predictions["true_intent"], predictions["pred_intent"])),
        "route_accuracy": float(accuracy_score(predictions["expected_route"], predictions["pred_route"])),
        "tier_accuracy": float(accuracy_score(predictions["expected_tier"], predictions["pred_tier"])),
        "avg_persona_confidence": float(predictions["persona_conf"].mean()),
        "avg_intent_confidence": float(predictions["intent_conf"].mean()),
        "easy_path_precision": safe_divide(
            ((easy_pred_mask) & (easy_gold_mask)).sum(),
            easy_pred_mask.sum(),
        ),
        "easy_path_recall": safe_divide(
            ((easy_pred_mask) & (easy_gold_mask)).sum(),
            easy_gold_mask.sum(),
        ),
        "llm_escalation_rate_if_below_0_60": float((predictions["intent_conf"] < 0.60).mean()),
        "llm_escalation_rate_if_below_0_70": float((predictions["intent_conf"] < 0.70).mean()),
        "route_accuracy_by_expected_tier": per_tier,
        "intent_confidence_bands": confidence_bands,
    }


def fit_predict_and_score(
    *,
    persona_builder: ModelBuilder,
    intent_builder: ModelBuilder,
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
) -> tuple[Pipeline, Pipeline, pd.DataFrame, dict[str, object]]:
    persona_model = persona_builder()
    intent_model = intent_builder()

    persona_model.fit(train_df["query_text"], train_df["persona"])
    intent_model.fit(train_df["query_text"], train_df["intent_label"])

    predictions = eval_df.copy()
    predictions["pred_persona"] = persona_model.predict(predictions["query_text"])
    predictions["pred_intent"] = intent_model.predict(predictions["query_text"])
    predictions["persona_conf"] = confidence_from_pipeline(persona_model, predictions["query_text"])
    predictions["intent_conf"] = confidence_from_pipeline(intent_model, predictions["query_text"])

    ruled = apply_strict_rule_layer(predictions, query_col="query_text")
    persona_rule_mask = ruled["rule_persona"] != ""
    intent_rule_mask = ruled["rule_intent"] != ""

    predictions.loc[persona_rule_mask, "pred_persona"] = ruled.loc[persona_rule_mask, "rule_persona"]
    predictions.loc[intent_rule_mask, "pred_intent"] = ruled.loc[intent_rule_mask, "rule_intent"]

    normalized_predictions = normalize_labeled_dataframe(
        predictions[["query_text", "pred_persona", "pred_intent"]].rename(
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
    predictions["pred_persona"] = normalized_predictions["persona"]
    predictions["pred_intent"] = normalized_predictions["intent_label"]
    predictions["pred_route"] = predictions["pred_intent"].map(ROUTE_MAP).fillna("fallback")
    predictions["pred_tier"] = predictions["pred_intent"].map(TIER_MAP).fillna("fallback")

    return persona_model, intent_model, predictions, compute_metrics(predictions)


def save_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--eval", required=True, type=Path)
    parser.add_argument("--out_dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_df = load_train(args.train)
    eval_df = load_eval(args.eval)

    train_df.to_csv(args.out_dir / "normalized_training_dataset.csv", index=False)
    eval_df.to_csv(args.out_dir / "normalized_evaluation_gold.csv", index=False)

    breakdown_from_series(train_df["intent_label"], label="intent_label").to_csv(
        args.out_dir / "train_intent_breakdown.csv",
        index=False,
    )
    breakdown_from_series(train_df["persona"], label="persona").to_csv(
        args.out_dir / "train_persona_breakdown.csv",
        index=False,
    )
    breakdown_from_series(eval_df["true_intent"], label="true_intent").to_csv(
        args.out_dir / "eval_intent_breakdown.csv",
        index=False,
    )
    breakdown_from_series(eval_df["true_persona"], label="true_persona").to_csv(
        args.out_dir / "eval_persona_breakdown.csv",
        index=False,
    )
    pd.crosstab(train_df["persona"], train_df["intent_label"]).to_csv(
        args.out_dir / "train_persona_intent_breakdown.csv"
    )
    breakdown_from_entity_types(train_df["entity_types"]).to_csv(
        args.out_dir / "train_entity_type_breakdown.csv",
        index=False,
    )
    breakdown_from_entity_types(eval_df["entity_types"]).to_csv(
        args.out_dir / "eval_entity_type_breakdown.csv",
        index=False,
    )

    normalization_summary = {
        "train_rows": int(len(train_df)),
        "eval_rows": int(len(eval_df)),
        "train_rows_with_normalization_flags": int((train_df["normalization_flags"] != "").sum()),
        "eval_rows_with_normalization_flags": int((eval_df["normalization_flags"] != "").sum()),
        "train_unique_intents": sorted(train_df["intent_label"].dropna().unique().tolist()),
        "eval_unique_intents": sorted(eval_df["true_intent"].dropna().unique().tolist()),
    }
    save_text(
        args.out_dir / "normalization_summary.json",
        json.dumps(normalization_summary, indent=2),
    )

    variant_specs: list[tuple[str, str, ModelBuilder, str, ModelBuilder]] = [
        ("normalized_nb", "nb", build_nb_model, "nb", build_nb_model),
        ("normalized_lsa_logreg", "lsa_logreg", build_lsa_logreg_model, "lsa_logreg", build_lsa_logreg_model),
        ("normalized_char_word_logreg", "char_word_logreg", build_char_word_logreg_model, "char_word_logreg", build_char_word_logreg_model),
        ("selected_mixed", "nb", build_nb_model, "char_word_logreg", build_char_word_logreg_model),
    ]

    comparison_rows: list[dict[str, object]] = []
    best_persona_model: Pipeline | None = None
    best_intent_model: Pipeline | None = None
    best_predictions: pd.DataFrame | None = None
    best_metrics: dict[str, object] | None = None

    for variant_name, persona_name, persona_builder, intent_name, intent_builder in variant_specs:
        persona_model, intent_model, predictions, metrics = fit_predict_and_score(
            persona_builder=persona_builder,
            intent_builder=intent_builder,
            train_df=train_df,
            eval_df=eval_df,
        )

        comparison_rows.append(
            {
                "variant": variant_name,
                "persona_model": persona_name,
                "intent_model": intent_name,
                "persona_accuracy": metrics["persona_accuracy"],
                "intent_accuracy": metrics["intent_accuracy"],
                "route_accuracy": metrics["route_accuracy"],
                "tier_accuracy": metrics["tier_accuracy"],
                "avg_intent_confidence": metrics["avg_intent_confidence"],
            }
        )

        if variant_name == "selected_mixed":
            best_persona_model = persona_model
            best_intent_model = intent_model
            best_predictions = predictions
            best_metrics = metrics

    raw_metrics_path = Path("outputs/metrics.json")
    if raw_metrics_path.exists():
        raw_metrics = json.loads(raw_metrics_path.read_text(encoding="utf-8"))
        comparison_rows.insert(
            0,
            {
                "variant": "original_packaged_outputs",
                "persona_model": "n/a",
                "intent_model": "n/a",
                "persona_accuracy": raw_metrics.get("persona_accuracy", 0.0),
                "intent_accuracy": raw_metrics.get("intent_accuracy", 0.0),
                "route_accuracy": raw_metrics.get("route_accuracy", 0.0),
                "tier_accuracy": "",
                "avg_intent_confidence": raw_metrics.get("avg_intent_confidence", 0.0),
            },
        )

    pd.DataFrame(comparison_rows).to_csv(args.out_dir / "model_comparison.csv", index=False)

    if best_persona_model is None or best_intent_model is None or best_predictions is None or best_metrics is None:
        raise RuntimeError("Selected mixed model was not produced.")

    joblib.dump(best_persona_model, args.out_dir / "persona_model.joblib")
    joblib.dump(best_intent_model, args.out_dir / "intent_model.joblib")
    best_predictions.to_csv(args.out_dir / "evaluation_predictions.csv", index=False)

    save_text(
        args.out_dir / "persona_report.txt",
        classification_report(best_predictions["true_persona"], best_predictions["pred_persona"], zero_division=0),
    )
    save_text(
        args.out_dir / "intent_report.txt",
        classification_report(best_predictions["true_intent"], best_predictions["pred_intent"], zero_division=0),
    )
    save_text(
        args.out_dir / "route_report.txt",
        classification_report(best_predictions["expected_route"], best_predictions["pred_route"], zero_division=0),
    )

    metrics_payload = {
        "selected_persona_model_variant": "nb",
        "selected_intent_model_variant": "char_word_logreg",
        "metrics": best_metrics,
    }
    save_text(args.out_dir / "metrics.json", json.dumps(metrics_payload, indent=2))

    summary_lines = [
        "Query Intent Resolver revised metrics summary",
        "",
        "Selected persona model: TF-IDF + Multinomial Naive Bayes",
        "Selected intent model: word+character TF-IDF + Logistic Regression",
        "",
        f"Persona accuracy: {best_metrics['persona_accuracy']:.2f}",
        f"Intent accuracy: {best_metrics['intent_accuracy']:.2f}",
        f"Route accuracy: {best_metrics['route_accuracy']:.2f}",
        f"Tier accuracy: {best_metrics['tier_accuracy']:.2f}",
        f"Average intent confidence: {best_metrics['avg_intent_confidence']:.2f}",
        f"Easy-path precision: {best_metrics['easy_path_precision']:.2f}",
        f"LLM escalation rate below 0.60 intent confidence: {best_metrics['llm_escalation_rate_if_below_0_60']:.2f}",
    ]
    save_text(args.out_dir / "metrics_summary.txt", "\n".join(summary_lines))

    print("Saved revised outputs to:", args.out_dir)
    print(json.dumps(metrics_payload, indent=2))


if __name__ == "__main__":
    main()

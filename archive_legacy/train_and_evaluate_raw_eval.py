"""
Training and evaluation pipeline for the new multi-source training data.

Design goals
------------
1. Treat the six new CSV files as the training source of truth.
2. Apply light, label-level standardization to training only.
3. Evaluate on the untouched raw gold set without aggressive post-hoc canonicalization.
4. Export accepted/rejected training rows so standardization stays auditable.

Example
-------
python train_and_evaluate_raw_eval.py \
  --base_dir . \
  --eval evaluation_gold_300_queries.csv \
  --out_dir outputs_newdata_raw_eval
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
    extract_entity_types,
)
from training_data_builder import write_standardized_dataset_artifacts


ModelBuilder = Callable[[], Pipeline]


def load_eval_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"query_text", "true_persona", "true_intent", "expected_route", "expected_tier"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Eval file missing columns: {sorted(missing)}")
    return df.copy()


def build_nb_model() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=25000,
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
            ("svd", TruncatedSVD(n_components=200, random_state=42)),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
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
                    max_features=30000,
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
                    max_features=25000,
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
                    max_iter=1500,
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

    predictions["pred_route"] = predictions["pred_intent"].map(ROUTE_MAP).fillna("fallback")
    predictions["pred_tier"] = predictions["pred_intent"].map(TIER_MAP).fillna("fallback")
    predictions["entity_types"] = predictions["query_text"].map(extract_entity_types)
    return persona_model, intent_model, predictions, compute_metrics(predictions)


def save_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", type=Path, default=Path("."))
    parser.add_argument("--eval", required=True, type=Path)
    parser.add_argument("--out_dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_df, rejected_df, training_summary = write_standardized_dataset_artifacts(
        base_dir=args.base_dir,
        out_dir=args.out_dir,
    )
    eval_df = load_eval_raw(args.eval)

    if train_df.empty:
        raise RuntimeError("No standardized training rows were accepted.")

    train_df["entity_types"] = train_df["query_text"].map(extract_entity_types)
    eval_df["entity_types"] = eval_df["query_text"].map(extract_entity_types)
    train_df.to_csv(args.out_dir / "standardized_training_dataset.csv", index=False)
    eval_df.to_csv(args.out_dir / "evaluation_gold_raw.csv", index=False)

    breakdown_from_series(train_df["intent_label"], label="intent_label").to_csv(
        args.out_dir / "train_intent_breakdown.csv",
        index=False,
    )
    breakdown_from_series(train_df["persona"], label="persona").to_csv(
        args.out_dir / "train_persona_breakdown.csv",
        index=False,
    )
    breakdown_from_series(train_df["source_file"], label="source_file").to_csv(
        args.out_dir / "train_source_breakdown.csv",
        index=False,
    )
    if not rejected_df.empty:
        breakdown_from_series(rejected_df["rejection_reason"], label="rejection_reason").to_csv(
            args.out_dir / "rejection_reason_breakdown.csv",
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

    variant_specs: list[tuple[str, str, ModelBuilder, str, ModelBuilder]] = [
        ("nb", "nb", build_nb_model, "nb", build_nb_model),
        ("lsa_logreg", "lsa_logreg", build_lsa_logreg_model, "lsa_logreg", build_lsa_logreg_model),
        ("char_word_logreg", "char_word_logreg", build_char_word_logreg_model, "char_word_logreg", build_char_word_logreg_model),
    ]

    comparison_rows: list[dict[str, object]] = []
    best_bundle: tuple[Pipeline, Pipeline, pd.DataFrame, dict[str, object], str, str] | None = None

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
        candidate = (metrics["route_accuracy"], metrics["intent_accuracy"], metrics["persona_accuracy"])
        if best_bundle is None:
            best_bundle = (persona_model, intent_model, predictions, metrics, persona_name, intent_name)
            best_score = candidate
        elif candidate > best_score:
            best_bundle = (persona_model, intent_model, predictions, metrics, persona_name, intent_name)
            best_score = candidate

    pd.DataFrame(comparison_rows).to_csv(args.out_dir / "model_comparison.csv", index=False)

    if best_bundle is None:
        raise RuntimeError("No model variant was produced.")

    best_persona_model, best_intent_model, best_predictions, best_metrics, best_persona_name, best_intent_name = best_bundle

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

    payload = {
        "selected_persona_model_variant": best_persona_name,
        "selected_intent_model_variant": best_intent_name,
        "training_standardization_summary": training_summary,
        "metrics": best_metrics,
    }
    save_text(args.out_dir / "metrics.json", json.dumps(payload, indent=2))

    summary_lines = [
        "Query Intent Resolver raw-eval metrics summary",
        "",
        f"Selected persona model: {best_persona_name}",
        f"Selected intent model: {best_intent_name}",
        "",
        f"Accepted training rows: {len(train_df)}",
        f"Rejected training rows: {len(rejected_df)}",
        f"Persona accuracy: {best_metrics['persona_accuracy']:.2f}",
        f"Intent accuracy: {best_metrics['intent_accuracy']:.2f}",
        f"Route accuracy: {best_metrics['route_accuracy']:.2f}",
        f"Tier accuracy: {best_metrics['tier_accuracy']:.2f}",
        f"Average intent confidence: {best_metrics['avg_intent_confidence']:.2f}",
        f"Easy-path precision: {best_metrics['easy_path_precision']:.2f}",
        "Evaluation note: gold labels were kept raw; only the training data was lightly standardized.",
    ]
    save_text(args.out_dir / "metrics_summary.txt", "\n".join(summary_lines))


if __name__ == "__main__":
    main()

"""
Primary route classifier for the Query Intent Resolver.

This script treats the handling approach as the main target:
  - shortcut
  - retrieval
  - llm
  - b2b

Persona and intent are preserved as metadata only and are not used as prediction targets.
Evaluation is done on a route-first macro mapping of the raw gold set.
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

from resolver_utils import apply_strict_rule_layer, confidence_from_pipeline, extract_entity_types
from training_data_builder import write_standardized_dataset_artifacts


ModelBuilder = Callable[[], Pipeline]

EXPECTED_ROUTE_TO_PRIMARY_ROUTE = {
    "typesense_only": "shortcut",
    "typesense_plus_metadata": "shortcut",
    "semantic_or_faceted_search": "retrieval",
    "foundry_multi_agent": "retrieval",
    "compare_pipeline": "retrieval",
    "recommendation_workflow": "retrieval",
    "faq_or_guidance": "retrieval",
    "finance_guidance": "retrieval",
    "outcomes_pipeline": "retrieval",
    "llm_advisory": "llm",
    "rewrite_then_route": "llm",
    "b2b_workflow": "b2b",
}

STRICT_INTENT_TO_PRIMARY_ROUTE = {
    "direct_lookup": "shortcut",
    "attribute_lookup": "shortcut",
    "b2b_partnership": "b2b",
}


def load_eval_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"query_text", "expected_route"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Eval file missing columns: {sorted(missing)}")
    df = df.copy()
    df["expected_primary_route"] = df["expected_route"].map(EXPECTED_ROUTE_TO_PRIMARY_ROUTE)
    if df["expected_primary_route"].isna().any():
        missing_routes = sorted(df.loc[df["expected_primary_route"].isna(), "expected_route"].dropna().unique().tolist())
        raise ValueError(f"Unmapped expected routes in eval file: {missing_routes}")
    return df


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
    shortcut_pred_mask = predictions["pred_primary_route"] == "shortcut"
    shortcut_gold_mask = predictions["expected_primary_route"] == "shortcut"
    llm_pred_mask = predictions["pred_primary_route"] == "llm"
    llm_gold_mask = predictions["expected_primary_route"] == "llm"
    b2b_pred_mask = predictions["pred_primary_route"] == "b2b"
    b2b_gold_mask = predictions["expected_primary_route"] == "b2b"

    return {
        "primary_route_accuracy": float(accuracy_score(predictions["expected_primary_route"], predictions["pred_primary_route"])),
        "avg_route_confidence": float(predictions["route_conf"].mean()),
        "shortcut_precision": safe_divide(((shortcut_pred_mask) & (shortcut_gold_mask)).sum(), shortcut_pred_mask.sum()),
        "shortcut_recall": safe_divide(((shortcut_pred_mask) & (shortcut_gold_mask)).sum(), shortcut_gold_mask.sum()),
        "llm_precision": safe_divide(((llm_pred_mask) & (llm_gold_mask)).sum(), llm_pred_mask.sum()),
        "llm_recall": safe_divide(((llm_pred_mask) & (llm_gold_mask)).sum(), llm_gold_mask.sum()),
        "b2b_precision": safe_divide(((b2b_pred_mask) & (b2b_gold_mask)).sum(), b2b_pred_mask.sum()),
        "b2b_recall": safe_divide(((b2b_pred_mask) & (b2b_gold_mask)).sum(), b2b_gold_mask.sum()),
        "llm_share_predicted": float((predictions["pred_primary_route"] == "llm").mean()),
        "shortcut_share_predicted": float((predictions["pred_primary_route"] == "shortcut").mean()),
    }


def fit_predict_and_score(
    *,
    model_builder: ModelBuilder,
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
) -> tuple[Pipeline, pd.DataFrame, dict[str, object]]:
    model = model_builder()
    model.fit(train_df["query_text"], train_df["primary_route"])

    predictions = eval_df.copy()
    predictions["pred_primary_route"] = model.predict(predictions["query_text"])
    predictions["route_conf"] = confidence_from_pipeline(model, predictions["query_text"])

    ruled = apply_strict_rule_layer(predictions, query_col="query_text")
    rule_mask = ruled["rule_intent"] != ""
    if rule_mask.any():
        predictions.loc[rule_mask, "pred_primary_route"] = ruled.loc[rule_mask, "rule_intent"].map(STRICT_INTENT_TO_PRIMARY_ROUTE).fillna(
            predictions.loc[rule_mask, "pred_primary_route"]
        )

    predictions["entity_types"] = predictions["query_text"].map(extract_entity_types)
    return model, predictions, compute_metrics(predictions)


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
    train_df.to_csv(args.out_dir / "standardized_training_dataset.csv", index=False)
    eval_df.to_csv(args.out_dir / "evaluation_gold_raw.csv", index=False)

    breakdown_from_series(train_df["primary_route"], label="primary_route").to_csv(
        args.out_dir / "train_primary_route_breakdown.csv",
        index=False,
    )
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
    breakdown_from_series(eval_df["expected_primary_route"], label="expected_primary_route").to_csv(
        args.out_dir / "eval_primary_route_breakdown.csv",
        index=False,
    )

    variant_specs: list[tuple[str, ModelBuilder]] = [
        ("nb", build_nb_model),
        ("lsa_logreg", build_lsa_logreg_model),
        ("char_word_logreg", build_char_word_logreg_model),
    ]

    comparison_rows: list[dict[str, object]] = []
    best_bundle: tuple[Pipeline, pd.DataFrame, dict[str, object], str] | None = None
    best_score: tuple[float, float] | None = None

    for variant_name, builder in variant_specs:
        model, predictions, metrics = fit_predict_and_score(
            model_builder=builder,
            train_df=train_df,
            eval_df=eval_df,
        )
        comparison_rows.append(
            {
                "variant": variant_name,
                "primary_route_accuracy": metrics["primary_route_accuracy"],
                "shortcut_precision": metrics["shortcut_precision"],
                "llm_precision": metrics["llm_precision"],
                "avg_route_confidence": metrics["avg_route_confidence"],
            }
        )
        candidate = (metrics["primary_route_accuracy"], metrics["shortcut_precision"])
        if best_score is None or candidate > best_score:
            best_bundle = (model, predictions, metrics, variant_name)
            best_score = candidate

    pd.DataFrame(comparison_rows).to_csv(args.out_dir / "model_comparison.csv", index=False)

    if best_bundle is None:
        raise RuntimeError("No route model variant was produced.")

    best_model, best_predictions, best_metrics, best_variant = best_bundle
    joblib.dump(best_model, args.out_dir / "primary_route_model.joblib")
    best_predictions.to_csv(args.out_dir / "evaluation_predictions.csv", index=False)

    save_text(
        args.out_dir / "primary_route_report.txt",
        classification_report(best_predictions["expected_primary_route"], best_predictions["pred_primary_route"], zero_division=0),
    )

    payload = {
        "selected_route_model_variant": best_variant,
        "training_standardization_summary": training_summary,
        "metrics": best_metrics,
    }
    save_text(args.out_dir / "metrics.json", json.dumps(payload, indent=2))

    summary_lines = [
        "Query Intent Resolver primary-route metrics summary",
        "",
        f"Selected route model: {best_variant}",
        f"Accepted training rows: {len(train_df)}",
        f"Rejected training rows: {len(rejected_df)}",
        f"Primary route accuracy: {best_metrics['primary_route_accuracy']:.2f}",
        f"Shortcut precision: {best_metrics['shortcut_precision']:.2f}",
        f"Shortcut recall: {best_metrics['shortcut_recall']:.2f}",
        f"LLM precision: {best_metrics['llm_precision']:.2f}",
        f"LLM recall: {best_metrics['llm_recall']:.2f}",
        f"B2B precision: {best_metrics['b2b_precision']:.2f}",
        f"Average route confidence: {best_metrics['avg_route_confidence']:.2f}",
        "Evaluation note: gold labels were mapped to 4 macro handling approaches; persona/intent remain metadata only.",
    ]
    save_text(args.out_dir / "metrics_summary.txt", "\n".join(summary_lines))


if __name__ == "__main__":
    main()

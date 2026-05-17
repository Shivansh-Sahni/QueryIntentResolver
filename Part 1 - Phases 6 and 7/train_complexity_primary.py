"""
Complexity-first training and evaluation for the original raw six-file dataset.

Primary target:
  - short_circuit
  - medium
  - complex
  - llm_needed

We keep preprocessing minimal:
  - drop header-like junk rows
  - optionally map the one inconsistent label `high`
  - no intent standardization

We sweep multiple feature/model combinations and report the best setups for:
  1. random row split (optimistic / duplicate-friendly)
  2. grouped-by-query split (stricter / duplicate-resistant)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit, StratifiedShuffleSplit
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

from training_data_builder import default_training_source_paths, slugify_label


TARGET_LABELS = ["short_circuit", "medium", "complex", "llm_needed"]


@dataclass
class DatasetVariant:
    name: str
    high_strategy: str
    use_persona: bool


class QueryStats(BaseEstimator, TransformerMixin):
    """Lightweight query-shape features that help separate routing complexity."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        series = pd.Series(X).fillna("").astype(str)
        rows: list[list[float]] = []
        for text in series:
            lower = text.lower().strip()
            tokens = lower.split()
            rows.append(
                [
                    len(lower),
                    len(tokens),
                    lower.count("?"),
                    lower.count(" and "),
                    lower.count(" with "),
                    int(" vs " in lower or "compare" in lower),
                    int(
                        any(
                            key in lower
                            for key in [
                                "scholarship",
                                "tuition",
                                "financial aid",
                                "fafsa",
                                "cost",
                            ]
                        )
                    ),
                    int(
                        any(
                            key in lower
                            for key in [
                                "apply",
                                "admission",
                                "deadline",
                                "essay",
                                "gpa",
                                "sat",
                            ]
                        )
                    ),
                    int(
                        any(
                            key in lower
                            for key in [
                                "vibe",
                                "fit",
                                "stress",
                                "normal people",
                                "culture",
                                "suffering",
                            ]
                        )
                    ),
                    int(
                        any(
                            key in lower
                            for key in [
                                "partner",
                                "api access",
                                "demo",
                                "districts",
                                "school profile",
                            ]
                        )
                    ),
                ]
            )
        return sparse.csr_matrix(rows, dtype=float)


def load_raw_complexity_dataset(base_dir: Path, *, high_strategy: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in default_training_source_paths(base_dir):
        df = pd.read_csv(path)
        df["source_file"] = path.name
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True)

    raw["query_text"] = raw["Query"].astype(str).str.strip()
    raw["persona_raw"] = raw["Persona"].astype(str).str.strip()
    raw["complexity_raw"] = raw["Complexity"].astype(str).str.strip()
    raw["complexity_label"] = raw["complexity_raw"].map(slugify_label)

    header_like = (
        raw["query_text"].str.lower().eq("query")
        | raw["complexity_raw"].str.lower().eq("complexity")
    )
    raw = raw.loc[~header_like].copy()

    if high_strategy == "to_complex":
        raw.loc[raw["complexity_label"] == "high", "complexity_label"] = "complex"
    elif high_strategy == "to_llm_needed":
        raw.loc[raw["complexity_label"] == "high", "complexity_label"] = "llm_needed"
    elif high_strategy == "drop":
        raw = raw.loc[raw["complexity_label"] != "high"].copy()
    else:
        raise ValueError(f"Unsupported high_strategy: {high_strategy}")

    raw = raw.loc[raw["complexity_label"].isin(TARGET_LABELS)].copy()
    raw["persona_feature"] = raw["persona_raw"].map(slugify_label)
    return raw.reset_index(drop=True)


def combine_query_persona(df: pd.DataFrame) -> pd.Series:
    return (
        df["query_text"].fillna("")
        + " __persona__ "
        + df["persona_feature"].fillna("")
    )


def build_word_nb(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
        text_input = "passthrough"
    else:
        text_input = None

    if text_input is None:
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
                ("clf", MultinomialNB()),
            ]
        )

    return Pipeline(
        steps=steps
        + [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=30000,
                ),
            ),
            ("clf", MultinomialNB()),
        ]
    )


def build_word_cnb(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
    return Pipeline(
        steps=steps
        + [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=30000,
                ),
            ),
            ("clf", ComplementNB()),
        ]
    )


def build_word_logreg(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
    return Pipeline(
        steps=steps
        + [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=35000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2500,
                    class_weight="balanced",
                    solver="saga",
                    random_state=42,
                ),
            ),
        ]
    )


def build_char_word_logreg(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
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
        steps=steps
        + [
            ("features", features),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="saga",
                    random_state=42,
                ),
            ),
        ]
    )


def build_lsa_logreg(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
    return Pipeline(
        steps=steps
        + [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    max_features=35000,
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


def build_linear_svc_calibrated(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
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
        steps=steps
        + [
            ("features", features),
            (
                "clf",
                CalibratedClassifierCV(
                    estimator=LinearSVC(class_weight="balanced", random_state=42),
                    cv=3,
                ),
            ),
        ]
    )


def build_linear_svc_stats(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
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
            ("stats", QueryStats()),
        ]
    )
    return Pipeline(
        steps=steps
        + [
            ("features", features),
            (
                "clf",
                LinearSVC(
                    C=0.5,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def build_sgd_log(*, use_persona: bool) -> Pipeline:
    steps: list[tuple[str, object]] = []
    if use_persona:
        steps.append(("combine", FunctionTransformer(combine_query_persona, validate=False)))
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
        steps=steps
        + [
            ("features", features),
            (
                "clf",
                SGDClassifier(
                    loss="log_loss",
                    alpha=1e-5,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


MODEL_BUILDERS: dict[str, Callable[..., Pipeline]] = {
    "word_nb": build_word_nb,
    "word_cnb": build_word_cnb,
    "word_logreg": build_word_logreg,
    "char_word_logreg": build_char_word_logreg,
    "lsa_logreg": build_lsa_logreg,
    "linear_svc_calibrated": build_linear_svc_calibrated,
    "linear_svc_stats": build_linear_svc_stats,
    "sgd_log": build_sgd_log,
}


def select_feature_frame(df: pd.DataFrame, *, use_persona: bool) -> pd.DataFrame | pd.Series:
    if use_persona:
        return df[["query_text", "persona_feature"]].copy()
    return df["query_text"]


def evaluate_one_split(
    *,
    df: pd.DataFrame,
    train_idx: pd.Index | list[int] | pd.Series | object,
    test_idx: pd.Index | list[int] | pd.Series | object,
    use_persona: bool,
    model_name: str,
) -> dict[str, object]:
    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()
    builder = MODEL_BUILDERS[model_name]
    model = builder(use_persona=use_persona)

    X_train = select_feature_frame(train_df, use_persona=use_persona)
    X_test = select_feature_frame(test_df, use_persona=use_persona)
    y_train = train_df["complexity_label"]
    y_test = test_df["complexity_label"]

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(X_test)
    elif hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(X_test), dtype=float)
        if scores.ndim == 1:
            scores = np.column_stack([-scores, scores])
        shifted = scores - scores.max(axis=1, keepdims=True)
        exp_scores = np.exp(shifted)
        probabilities = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    else:
        probabilities = np.ones((len(test_df), len(TARGET_LABELS)), dtype=float)
        probabilities /= len(TARGET_LABELS)
    confidences = probabilities.max(axis=1)

    result = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "avg_confidence": float(confidences.mean()),
        "model": model,
        "y_test": y_test,
        "predictions": predictions,
        "test_df": test_df,
    }
    return result


def run_experiments(base_dir: Path) -> tuple[pd.DataFrame, dict[str, object], dict[str, object], pd.DataFrame]:
    rows: list[dict[str, object]] = []
    best_random: dict[str, object] | None = None
    best_grouped: dict[str, object] | None = None
    best_random_score = -1.0
    best_grouped_score = -1.0
    final_dataset_for_best: pd.DataFrame | None = None

    dataset_variants = [
        DatasetVariant(name="high_to_complex_query_only", high_strategy="to_complex", use_persona=False),
        DatasetVariant(name="high_to_complex_query_plus_persona", high_strategy="to_complex", use_persona=True),
        DatasetVariant(name="high_to_llm_query_only", high_strategy="to_llm_needed", use_persona=False),
        DatasetVariant(name="high_to_llm_query_plus_persona", high_strategy="to_llm_needed", use_persona=True),
        DatasetVariant(name="drop_high_query_only", high_strategy="drop", use_persona=False),
        DatasetVariant(name="drop_high_query_plus_persona", high_strategy="drop", use_persona=True),
    ]

    for variant in dataset_variants:
        df = load_raw_complexity_dataset(base_dir, high_strategy=variant.high_strategy)
        if final_dataset_for_best is None and variant.name == "high_to_complex_query_only":
            final_dataset_for_best = df.copy()

        stratified = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        random_train_idx, random_test_idx = next(stratified.split(df, df["complexity_label"]))

        groups = df["query_text"].str.lower().str.strip()
        grouped = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        grouped_train_idx, grouped_test_idx = next(grouped.split(df, df["complexity_label"], groups=groups))

        for model_name in MODEL_BUILDERS:
            random_result = evaluate_one_split(
                df=df,
                train_idx=random_train_idx,
                test_idx=random_test_idx,
                use_persona=variant.use_persona,
                model_name=model_name,
            )
            grouped_result = evaluate_one_split(
                df=df,
                train_idx=grouped_train_idx,
                test_idx=grouped_test_idx,
                use_persona=variant.use_persona,
                model_name=model_name,
            )

            rows.append(
                {
                    "variant": variant.name,
                    "high_strategy": variant.high_strategy,
                    "use_persona": variant.use_persona,
                    "model_name": model_name,
                    "random_accuracy": random_result["accuracy"],
                    "random_avg_confidence": random_result["avg_confidence"],
                    "grouped_accuracy": grouped_result["accuracy"],
                    "grouped_avg_confidence": grouped_result["avg_confidence"],
                    "rows_used": len(df),
                    "unique_queries": int(df["query_text"].nunique()),
                }
            )

            if random_result["accuracy"] > best_random_score:
                best_random_score = random_result["accuracy"]
                best_random = {
                    "variant": variant,
                    "model_name": model_name,
                    "result": random_result,
                    "split_type": "random_row_split",
                    "dataset": df.copy(),
                }
            if grouped_result["accuracy"] > best_grouped_score:
                best_grouped_score = grouped_result["accuracy"]
                best_grouped = {
                    "variant": variant,
                    "model_name": model_name,
                    "result": grouped_result,
                    "split_type": "grouped_query_split",
                    "dataset": df.copy(),
                }

    if best_random is None or best_grouped is None or final_dataset_for_best is None:
        raise RuntimeError("Experiment sweep failed to produce results.")

    return pd.DataFrame(rows), best_random, best_grouped, final_dataset_for_best


def save_best_artifacts(out_dir: Path, prefix: str, best_bundle: dict[str, object]) -> None:
    variant: DatasetVariant = best_bundle["variant"]
    result = best_bundle["result"]
    test_df = result["test_df"].copy()
    test_df["pred_complexity"] = result["predictions"]

    joblib.dump(result["model"], out_dir / f"{prefix}_model.joblib")
    test_df.to_csv(out_dir / f"{prefix}_predictions.csv", index=False)
    report = classification_report(result["y_test"], result["predictions"], zero_division=0)
    (out_dir / f"{prefix}_report.txt").write_text(report, encoding="utf-8")

    metadata = {
        "split_type": best_bundle["split_type"],
        "dataset_variant": variant.name,
        "high_strategy": variant.high_strategy,
        "use_persona": variant.use_persona,
        "model_name": best_bundle["model_name"],
        "accuracy": result["accuracy"],
        "avg_confidence": result["avg_confidence"],
    }
    (out_dir / f"{prefix}_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", type=Path, default=Path("."))
    parser.add_argument("--out_dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    leaderboard, best_random, best_grouped, dataset_snapshot = run_experiments(args.base_dir)
    leaderboard = leaderboard.sort_values(["grouped_accuracy", "random_accuracy"], ascending=False).reset_index(drop=True)
    leaderboard.to_csv(args.out_dir / "experiment_leaderboard.csv", index=False)

    dataset_snapshot.to_csv(args.out_dir / "complexity_dataset_snapshot.csv", index=False)
    dataset_summary = {
        "rows": int(len(dataset_snapshot)),
        "unique_queries": int(dataset_snapshot["query_text"].nunique()),
        "complexity_breakdown": dataset_snapshot["complexity_label"].value_counts().to_dict(),
        "persona_breakdown": dataset_snapshot["persona_feature"].value_counts().to_dict(),
    }
    (args.out_dir / "dataset_summary.json").write_text(json.dumps(dataset_summary, indent=2), encoding="utf-8")

    save_best_artifacts(args.out_dir, "best_random", best_random)
    save_best_artifacts(args.out_dir, "best_grouped", best_grouped)

    summary_lines = [
        "Complexity classification sweep summary",
        "",
        f"Best random-row accuracy: {best_random['result']['accuracy']:.4f}",
        f"Best random-row setup: {best_random['variant'].name} + {best_random['model_name']}",
        f"Best grouped-query accuracy: {best_grouped['result']['accuracy']:.4f}",
        f"Best grouped-query setup: {best_grouped['variant'].name} + {best_grouped['model_name']}",
        "",
        "Note: random-row split can benefit from repeated queries across train/test.",
        "Grouped-query split is the stricter estimate for generalization to unseen query strings.",
    ]
    (args.out_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")


if __name__ == "__main__":
    main()

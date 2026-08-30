from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin


class QueryStats(BaseEstimator, TransformerMixin):
    """Deterministic query-shape features used alongside word and character TF-IDF."""

    FEATURE_NAMES = (
        "character_count",
        "token_count",
        "question_mark_count",
        "comma_count",
        "and_count",
        "with_count",
        "or_count",
        "comparison_signal",
        "recommendation_signal",
        "cost_signal",
        "admissions_signal",
        "subjective_signal",
        "b2b_signal",
        "number_count",
    )

    def fit(self, X, y=None):  # noqa: N803
        return self

    def transform(self, X):  # noqa: N803
        series = pd.Series(X).fillna("").astype(str)
        rows: list[list[float]] = []
        for text in series:
            lower = text.casefold().strip()
            tokens = lower.split()
            rows.append(
                [
                    min(float(len(lower)) / 200.0, 1.0),
                    min(float(len(tokens)) / 50.0, 1.0),
                    min(float(lower.count("?")) / 3.0, 1.0),
                    min(float(lower.count(",")) / 5.0, 1.0),
                    min(float(lower.count(" and ")) / 5.0, 1.0),
                    min(float(lower.count(" with ")) / 5.0, 1.0),
                    min(float(lower.count(" or ")) / 5.0, 1.0),
                    float(int(" vs " in lower or "compare" in lower or "difference between" in lower)),
                    float(
                        int(
                            any(
                                term in lower
                                for term in (
                                    "recommend",
                                    "what schools should",
                                    "best colleges for me",
                                    "schools like",
                                    "build a list",
                                    "reach target safety",
                                )
                            )
                        )
                    ),
                    float(
                        int(
                            any(
                                term in lower
                                for term in (
                                    "tuition",
                                    "cost",
                                    "financial aid",
                                    "fafsa",
                                    "scholarship",
                                    "under $",
                                )
                            )
                        )
                    ),
                    float(
                        int(
                            any(
                                term in lower
                                for term in ("apply", "admission", "deadline", "essay", "gpa", "sat", "act")
                            )
                        )
                    ),
                    float(
                        int(
                            any(
                                term in lower
                                for term in (
                                    "vibe",
                                    "fit",
                                    "stress",
                                    "normal people",
                                    "culture",
                                    "suffering",
                                    "introvert",
                                    "feel like",
                                )
                            )
                        )
                    ),
                    float(
                        int(
                            any(
                                term in lower
                                for term in (
                                    "partner",
                                    "api access",
                                    "request demo",
                                    "district",
                                    "school profile",
                                    "institutional",
                                )
                            )
                        )
                    ),
                    min(float(len(re.findall(r"\d+(?:\.\d+)?", lower))) / 5.0, 1.0),
                ]
            )
        return sparse.csr_matrix(np.asarray(rows, dtype=float))

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.FEATURE_NAMES, dtype=object)


# Backward-compatible alias for earlier prototypes.
QueryShapeFeatures = QueryStats

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from .common import ROUTES, SEED, SCHOOLS, family_id, family_text, normalize

SCHOOL_PATTERN = "(?:" + "|".join(re.escape(s) for s in sorted(SCHOOLS, key=len, reverse=True)) + ")"
ATTR_PATTERN = r"(?:tuition|acceptance rate|application deadline|admissions deadline|mascot|location|address|housing guarantee|student faculty ratio|average sat|average gpa)"
LOOKUP_PATTERNS = tuple(re.compile(p) for p in (
    SCHOOL_PATTERN,
    SCHOOL_PATTERN + r"(?:'s)? " + ATTR_PATTERN,
    ATTR_PATTERN + r" (?:at|for|of) " + SCHOOL_PATTERN,
    r"(?:what is|what's|show me|tell me) (?:the )?" + SCHOOL_PATTERN + r"(?:'s)? " + ATTR_PATTERN,
    r"(?:what is|what's|show me|tell me) (?:the )?" + ATTR_PATTERN + r" (?:at|for|of) " + SCHOOL_PATTERN,
    r"where is " + SCHOOL_PATTERN,
))
GUARD = re.compile(r"\b(?:weather tomorrow|weather forecast|chocolate cake recipe|pasta recipe|ignore (?:all |the |previous )*instructions|reveal (?:your |the )?system prompt|print (?:your |the )?api key|write ransomware|steal passwords)\b")

def policy_rule(query: str) -> str | None:
    q = normalize(query).strip(" .?!")
    return "short_circuit" if any(p.fullmatch(q) for p in LOOKUP_PATTERNS) else None

def input_guard(query: str) -> bool:
    q = normalize(query)
    if GUARD.search(q):
        return True
    letters = [c for c in q if c.isalpha()]
    if not letters:
        return True
    return sum(c.isascii() for c in letters) / len(letters) < 0.5

def vector_model(kind: str) -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), max_features=40000, sublinear_tf=True, strip_accents="unicode")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=45000, sublinear_tf=True, strip_accents="unicode")),
        ("generalized", TfidfVectorizer(preprocessor=family_text, lowercase=False, ngram_range=(1, 2), max_features=18000, sublinear_tf=True)),
    ], transformer_weights={"word": 1.0, "char": 0.7, "generalized": 0.8})
    choices = {
        "logistic": LogisticRegression(C=3.0, class_weight="balanced", max_iter=1500, tol=1e-3, random_state=SEED),
        "linearsvc": LinearSVC(C=1.2, class_weight="balanced", max_iter=10000, tol=1e-3, dual="auto", random_state=SEED),
        "sgd": SGDClassifier(loss="log_loss", alpha=0.0001, class_weight="balanced", max_iter=2000, tol=1e-4, random_state=SEED),
    }
    if kind not in choices:
        raise ValueError("Unsupported preregistered candidate")
    return Pipeline([("features", features), ("classifier", choices[kind])])

def group_splits(frame: pd.DataFrame, folds: int = 3, seed: int = SEED):
    groups = frame.query_text.map(family_id).to_numpy()
    y = frame.route.to_numpy()
    splits = list(StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed).split(frame.query_text, y, groups))
    for train, valid in splits:
        if set(groups[train]) & set(groups[valid]):
            raise AssertionError("Template group leakage")
        if set(y[train]) != set(ROUTES) or set(y[valid]) != set(ROUTES):
            raise ValueError("A grouped fold lacks a route; do not silently substitute a row-level split")
    return splits

def fit_model(kind: str, frame: pd.DataFrame) -> CalibratedClassifierCV:
    # Fit the entire text pipeline inside each grouped calibration fold.
    model = CalibratedClassifierCV(vector_model(kind), method="sigmoid", cv=group_splits(frame), n_jobs=1, ensemble=True)
    model.fit(frame.query_text.to_numpy(), frame.route.to_numpy())
    return model

def probabilities(model, queries: list[str] | np.ndarray) -> np.ndarray:
    p = model.predict_proba(queries)
    lookup = {label: i for i, label in enumerate(model.classes_)}
    p = p[:, [lookup[label] for label in ROUTES]]
    if not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError("Invalid probability matrix")
    return p

@dataclass
class RoutingPolicy:
    short_threshold: float = 0.8
    low_threshold: float = 0.45
    use_lookup_rules: bool = False
    rule_confidence: float = 0.0

    def decide(self, query: str, p: np.ndarray) -> dict[str, Any]:
        if input_guard(query):
            return {"route": "llm_needed", "confidence": 0.0, "decision_source": "unsupported_or_guarded_input", "raw_route": ROUTES[int(p.argmax())]}
        raw_i = int(p.argmax())
        raw_route = ROUTES[raw_i]
        if self.use_lookup_rules and policy_rule(query):
            return {"route": "short_circuit", "confidence": float(self.rule_confidence), "decision_source": "validated_lookup_rule", "raw_route": raw_route}
        source = "calibrated_model"
        i = raw_i
        if raw_route == "short_circuit" and p[0] < self.short_threshold:
            i = 1 + int(p[1:].argmax())
            source = "short_circuit_gate"
        if p[i] < self.low_threshold:
            i = ROUTES.index("llm_needed")
            source = "low_confidence_fallback"
        return {"route": ROUTES[i], "confidence": float(p[i]), "decision_source": source, "raw_route": raw_route}

    def apply(self, queries: list[str], p: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame([self.decide(q, row) for q, row in zip(queries, p)])

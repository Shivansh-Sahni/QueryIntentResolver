from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np

from .policy import apply_deployment_policy, load_route_policy

VALID_ROUTES = {"short_circuit", "medium", "complex", "llm_needed"}


class QueryIntentResolver:
    """Stable V1 resolver interface for raw-query routing classification."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        model: Any | None = None,
        policy_path: str | Path | None = None,
        policy: dict[str, Any] | None = None,
    ) -> None:
        if model is None and model_path is None:
            raise ValueError("Provide model_path or model")
        self.model = model if model is not None else joblib.load(Path(model_path))
        self.policy = policy or load_route_policy(policy_path)

    def _raw_prediction(self, query_texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
        probabilities = np.asarray(self.model.predict_proba(query_texts), dtype=float)
        classes = np.asarray(self.model.classes_, dtype=object)
        best_indices = probabilities.argmax(axis=1)
        routes = classes[best_indices].astype(str)
        confidences = probabilities[np.arange(len(probabilities)), best_indices]
        unknown = set(routes) - VALID_ROUTES
        if unknown:
            raise RuntimeError(f"Model returned invalid routes: {sorted(unknown)}")
        return routes, confidences

    def resolve(
        self,
        query_text: str,
        *,
        persona: str | None = None,
        page: str | None = None,
        filters: dict[str, Any] | None = None,
        context: list[dict[str, Any]] | dict[str, Any] | None = None,
        session: dict[str, Any] | None = None,
        include_optional_fields: bool = False,
        include_optional: bool | None = None,
    ) -> dict[str, Any]:
        # These fields are accepted to preserve future compatibility but are deliberately
        # decoupled from V1 inference. V1 consumes raw query text only.
        del persona, page, filters, context, session

        text = str(query_text).strip()
        if not text:
            raise ValueError("query_text must be a non-empty string")

        started = time.perf_counter()
        raw_routes, confidences = self._raw_prediction([text])
        latency_ms = (time.perf_counter() - started) * 1000.0
        raw_route = str(raw_routes[0])
        confidence = float(confidences[0])
        route, reason = apply_deployment_policy(raw_route, confidence, self.policy)

        response: dict[str, Any] = {
            "route": route,
            "confidence": round(confidence, 6),
        }
        include_debug = include_optional_fields or bool(include_optional)
        if include_debug:
            response.update(
                {
                    "entities": {},
                    "intent": None,
                    "raw_route": raw_route,
                    "policy_reason": reason,
                    "latency_ms": round(latency_ms, 6),
                    "context_used": False,
                }
            )
        return response

    def resolve_batch(self, query_texts: Iterable[str]) -> list[dict[str, Any]]:
        texts = [str(value).strip() for value in query_texts]
        if not texts or any(not value for value in texts):
            raise ValueError("All query_text values must be non-empty strings")
        raw_routes, confidences = self._raw_prediction(texts)
        outputs: list[dict[str, Any]] = []
        for raw_route, confidence in zip(raw_routes, confidences):
            route, _ = apply_deployment_policy(str(raw_route), float(confidence), self.policy)
            outputs.append({"route": route, "confidence": round(float(confidence), 6)})
        return outputs

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "route_policy.json"


def load_route_policy(path: str | Path | None = None) -> dict[str, Any]:
    policy_path = Path(path) if path else DEFAULT_POLICY_PATH
    with policy_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_deployment_policy(
    predicted_route: str,
    confidence: float,
    policy: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Apply conservative routing overrides and return route plus reason."""
    policy = policy or load_route_policy()
    valid_routes = set(policy["valid_routes"])
    deployment = policy["deployment_policy"]

    if predicted_route not in valid_routes:
        return deployment["low_confidence_route"], "invalid_prediction_fallback"

    if confidence < float(deployment["global_low_confidence_threshold"]):
        return deployment["low_confidence_route"], "global_low_confidence_escalation"

    if (
        predicted_route == "short_circuit"
        and confidence < float(deployment["short_circuit_min_confidence"])
    ):
        return deployment["unsafe_short_circuit_route"], "short_circuit_safety_escalation"

    return predicted_route, "accepted_model_prediction"

from __future__ import annotations

from qir_v1.policy import apply_deployment_policy, load_route_policy


def test_low_confidence_escalates_to_llm() -> None:
    policy = load_route_policy()
    route, reason = apply_deployment_policy("complex", 0.20, policy)
    assert route == "llm_needed"
    assert reason == "global_low_confidence_escalation"


def test_unsafe_short_circuit_escalates_to_medium() -> None:
    policy = load_route_policy()
    route, reason = apply_deployment_policy("short_circuit", 0.70, policy)
    assert route == "medium"
    assert reason == "short_circuit_safety_escalation"


def test_high_confidence_prediction_is_accepted() -> None:
    policy = load_route_policy()
    route, reason = apply_deployment_policy("short_circuit", 0.95, policy)
    assert route == "short_circuit"
    assert reason == "accepted_model_prediction"

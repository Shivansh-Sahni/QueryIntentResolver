from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qir_v1.resolver import QueryIntentResolver


class DummyModel:
    classes_ = np.asarray(["complex", "llm_needed", "medium", "short_circuit"])

    def __init__(self, probabilities):
        self.probabilities = np.asarray(probabilities, dtype=float)

    def predict_proba(self, queries):
        return np.tile(self.probabilities, (len(queries), 1))


def test_v1_contract_and_optional_inputs_are_decoupled() -> None:
    resolver = QueryIntentResolver(model=DummyModel([0.05, 0.05, 0.10, 0.80]))
    output = resolver.resolve("MIT", persona="parent", page="search", filters={"state": "CA"})
    assert output == {"route": "short_circuit", "confidence": 0.8}


def test_low_confidence_forces_safe_llm_route() -> None:
    resolver = QueryIntentResolver(model=DummyModel([0.30, 0.20, 0.25, 0.25]))
    output = resolver.resolve("unclear request", include_optional_fields=True)
    assert output["route"] == "llm_needed"
    assert output["policy_reason"] == "global_low_confidence_escalation"
    assert output["raw_route"] == "complex"
    assert output["context_used"] is False

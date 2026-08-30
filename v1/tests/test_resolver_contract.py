from __future__ import annotations

import numpy as np
import pytest

from qir_v1.resolver import QueryIntentResolver


class FakeModel:
    classes_ = np.asarray(["complex", "llm_needed", "medium", "short_circuit"])

    def __init__(self, probabilities):
        self.probabilities = np.asarray([probabilities], dtype=float)

    def predict_proba(self, values):
        return np.repeat(self.probabilities, len(values), axis=0)


def test_default_output_is_exact_v1_contract() -> None:
    resolver = QueryIntentResolver(model=FakeModel([0.02, 0.03, 0.05, 0.90]))
    result = resolver.resolve("MIT")
    assert result == {"route": "short_circuit", "confidence": 0.9}


def test_optional_inputs_are_decoupled_and_ignored() -> None:
    resolver = QueryIntentResolver(model=FakeModel([0.10, 0.10, 0.70, 0.10]))
    result = resolver.resolve(
        "colleges in California",
        persona="parent",
        page="search",
        filters={"state": "CA"},
        context=[{"role": "user", "content": "prior"}],
        session={"id": "abc"},
        include_optional=True,
    )
    assert result["route"] == "medium"
    assert result["context_used"] is False
    assert result["entities"] == {}
    assert result["intent"] is None


def test_empty_query_is_rejected() -> None:
    resolver = QueryIntentResolver(model=FakeModel([0.25, 0.25, 0.25, 0.25]))
    with pytest.raises(ValueError):
        resolver.resolve("   ")

from __future__ import annotations

import pandas as pd

from qir_v1.evaluation import evaluate_routes


def test_false_short_circuit_metric() -> None:
    gold = pd.DataFrame(
        {
            "benchmark_id": ["1", "2", "3", "4"],
            "query_text": ["a", "b", "c", "d"],
            "route": ["short_circuit", "medium", "complex", "llm_needed"],
        }
    )
    pred = pd.DataFrame(
        {
            "benchmark_id": ["1", "2", "3", "4"],
            "predicted_route": ["short_circuit", "short_circuit", "complex", "llm_needed"],
            "confidence": [0.9, 0.8, 0.8, 0.8],
            "latency_ms": [1.0, 1.0, 1.0, 1.0],
            "estimated_cost_usd": [0.0, 0.0, 0.0, 0.0],
        }
    )
    metrics = evaluate_routes(gold, pred, model_name="test")
    assert metrics["false_short_circuit_count"] == 1
    assert metrics["false_short_circuit_rate"] == 0.5
    assert metrics["short_circuit_recall"] == 1.0

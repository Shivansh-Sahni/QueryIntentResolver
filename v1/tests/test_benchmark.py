from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "freeze_benchmark.py"
spec = importlib.util.spec_from_file_location("freeze_benchmark_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_benchmark_is_deterministic_balanced_and_disjoint(tmp_path: Path) -> None:
    rows = []
    for route_index, route in enumerate(module.ROUTES):
        for index in range(30):
            rows.append(
                {
                    "query_id": f"{route_index}-{index}",
                    "query_text": f"{route} query {index}",
                    "query_norm": f"{route} query {index}",
                    "route": route,
                    "resolution_method": "unanimous_observed",
                    "resolution_confidence": 1.0,
                    "resolution_note": "test",
                    "row_count": 1,
                    "observed_intents": "",
                    "observed_personas": "",
                    "source_files": "sample.csv",
                }
            )
    cleaned = tmp_path / "cleaned.csv"
    pd.DataFrame(rows).to_csv(cleaned, index=False)

    output_a = tmp_path / "a"
    output_b = tmp_path / "b"
    lock_a = module.freeze_benchmark(
        cleaned,
        output_a,
        benchmark_size=40,
        min_per_class=5,
        seed=7,
        min_resolution_confidence=0.95,
        allowed_methods={"unanimous_observed"},
    )
    lock_b = module.freeze_benchmark(
        cleaned,
        output_b,
        benchmark_size=40,
        min_per_class=5,
        seed=7,
        min_resolution_confidence=0.95,
        allowed_methods={"unanimous_observed"},
    )

    bench = pd.read_csv(output_a / "benchmark_gold.csv")
    train = pd.read_csv(output_a / "training_clean.csv")
    assert len(bench) == 40
    assert bench["route"].value_counts().to_dict() == {route: 10 for route in module.ROUTES}
    assert not (set(bench["query_id"]) & set(train["query_id"]))
    assert lock_a["manifest"]["benchmark_gold_sha256"] == lock_b["manifest"]["benchmark_gold_sha256"]

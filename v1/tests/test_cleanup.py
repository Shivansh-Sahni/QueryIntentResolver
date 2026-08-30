from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "clean_routing_labels.py"
spec = importlib.util.spec_from_file_location("clean_routing_labels_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_conflicts_are_resolved_or_quarantined(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(
        [
            {"Query": "MIT", "Persona": "student", "Intent": "exact_lookup", "Complexity": "medium"},
            {"Query": " mit ", "Persona": "parent", "Intent": "exact_lookup", "Complexity": "short_circuit"},
            {
                "Query": "schools with normal people",
                "Persona": "student",
                "Intent": "campus_life_fit",
                "Complexity": "complex",
            },
            {
                "Query": "schools with normal people",
                "Persona": "student",
                "Intent": "campus_life_fit",
                "Complexity": "llm_needed",
            },
            {"Query": "unknown stable", "Persona": "student", "Intent": "unknown", "Complexity": "medium"},
            {"Query": "unknown tie", "Persona": "student", "Intent": "unknown", "Complexity": "medium"},
            {"Query": "unknown tie", "Persona": "student", "Intent": "unknown", "Complexity": "complex"},
            {"Query": "junk", "Persona": "student", "Intent": "unknown", "Complexity": "high"},
        ]
    ).to_csv(data_dir / "sample.csv", index=False)

    policy = module.load_policy(Path(__file__).resolve().parents[1] / "config" / "route_policy.json")
    raw, _ = module.load_sources(data_dir, policy)
    resolution = module.build_resolution_table(
        raw,
        valid_routes=set(policy["valid_routes"]),
        intent_to_route=policy["intent_to_route"],
        overrides={},
    )
    by_query = resolution.set_index("query_norm")

    # Because the historical labels conflict, the canonical intent policy fixes the entity lookup.
    assert by_query.loc["mit", "resolved_route"] == "short_circuit"
    assert by_query.loc["mit", "resolution_method"] == "intent_policy"
    assert by_query.loc["schools with normal people", "resolved_route"] == "llm_needed"
    assert by_query.loc["unknown stable", "resolved_route"] == "medium"
    assert by_query.loc["unknown stable", "resolution_method"] == "unanimous_observed"
    assert by_query.loc["unknown tie", "resolution_method"] == "manual_review"
    assert by_query.loc["junk", "resolution_method"] == "manual_review"

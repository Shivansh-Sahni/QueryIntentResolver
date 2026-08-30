from pathlib import Path
import subprocess
import sys

import pandas as pd


def test_manual_review_merge(tmp_path: Path) -> None:
    reviewed = tmp_path / "review.csv"
    overrides = tmp_path / "overrides.csv"
    pd.DataFrame(
        [
            {
                "query_text": "MIT but cheaper",
                "review_route": "complex",
                "reviewer": "test",
                "review_notes": "recommendation",
            }
        ]
    ).to_csv(reviewed, index=False)
    pd.DataFrame(
        [{"query_text": "MIT", "route": "short_circuit", "rationale": "lookup"}]
    ).to_csv(overrides, index=False)

    subprocess.run(
        [
            sys.executable,
            "v1/scripts/apply_manual_review.py",
            "--reviewed",
            str(reviewed),
            "--overrides",
            str(overrides),
            "--reviewer-required",
        ],
        check=True,
    )
    result = pd.read_csv(overrides)
    assert set(result["route"]) == {"short_circuit", "complex"}
    assert len(result) == 2

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the exact benchmark input required for Anthony's Qwen model")
    parser.add_argument("--benchmark-queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.benchmark_queries, dtype=str, keep_default_na=False)
    id_col = "benchmark_id" if "benchmark_id" in df.columns else "benchmark_row_id" if "benchmark_row_id" in df.columns else None
    required = {"query_id", "query_text"}
    missing = required - set(df.columns)
    if id_col is None:
        missing.add("benchmark_id or benchmark_row_id")
    if missing:
        raise ValueError(f"Benchmark query file is missing: {sorted(missing)}")

    output = pd.DataFrame(
        {
            "benchmark_id": df[id_col],
            "benchmark_row_id": df[id_col],
            "query_id": df["query_id"],
            "query_text": df["query_text"],
            "instruction": "Classify this college-related query. Return persona and intent.",
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(f"Wrote {len(output)} Qwen benchmark rows to {args.output}")


if __name__ == "__main__":
    main()

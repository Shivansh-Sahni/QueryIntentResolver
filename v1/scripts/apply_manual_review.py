from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

VALID_ROUTES = {"short_circuit", "medium", "complex", "llm_needed"}


def normalize_query(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate reviewed manual-label decisions and merge them into the V1 override file"
    )
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--overrides", type=Path, default=Path("v1/data/manual_overrides.csv"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--reviewer-required", action="store_true")
    args = parser.parse_args()

    reviewed = pd.read_csv(args.reviewed, dtype=str, keep_default_na=False)
    required = {"query_text", "review_route"}
    if missing := required - set(reviewed.columns):
        raise ValueError(f"Reviewed file is missing columns: {sorted(missing)}")

    reviewed["query_norm"] = reviewed["query_text"].map(normalize_query)
    reviewed["route"] = reviewed["review_route"].str.strip().str.casefold()
    selected = reviewed.loc[reviewed["route"].ne("")].copy()
    invalid = sorted(set(selected["route"]) - VALID_ROUTES)
    if invalid:
        raise ValueError(f"Invalid review routes: {invalid}")
    if selected["query_norm"].eq("").any():
        raise ValueError("Reviewed rows contain blank queries")
    if selected["query_norm"].duplicated().any():
        duplicates = selected.loc[selected["query_norm"].duplicated(False), "query_text"].tolist()
        raise ValueError(f"Reviewed file contains duplicate query decisions: {duplicates[:10]}")
    if args.reviewer_required:
        if "reviewer" not in selected.columns or selected["reviewer"].str.strip().eq("").any():
            raise ValueError("Every selected review decision must include a reviewer")

    if args.overrides.exists():
        current = pd.read_csv(args.overrides, dtype=str, keep_default_na=False)
    else:
        current = pd.DataFrame(columns=["query_text", "route", "rationale"])
    required_override = {"query_text", "route"}
    if missing := required_override - set(current.columns):
        raise ValueError(f"Override file is missing columns: {sorted(missing)}")
    if "rationale" not in current.columns:
        current["rationale"] = ""
    current["query_norm"] = current["query_text"].map(normalize_query)

    new_rows: list[dict[str, str]] = []
    for row in selected.itertuples(index=False):
        reviewer = getattr(row, "reviewer", "").strip()
        notes = getattr(row, "review_notes", "").strip()
        rationale = notes or "Manual adjudication"
        if reviewer:
            rationale = f"{rationale} (reviewer: {reviewer})"
        new_rows.append(
            {
                "query_text": row.query_text.strip(),
                "query_norm": row.query_norm,
                "route": row.route,
                "rationale": rationale,
            }
        )

    additions = pd.DataFrame(new_rows)
    combined = pd.concat([current, additions], ignore_index=True)
    combined = combined.drop_duplicates(subset=["query_norm"], keep="last")
    combined = combined.sort_values("query_norm").reset_index(drop=True)
    output = args.output or args.overrides
    output.parent.mkdir(parents=True, exist_ok=True)
    combined[["query_text", "route", "rationale"]].to_csv(
        output, index=False, quoting=csv.QUOTE_MINIMAL
    )

    summary = {
        "review_rows_seen": int(len(reviewed)),
        "review_decisions_applied": int(len(additions)),
        "total_overrides_after_merge": int(len(combined)),
        "output": str(output),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

VALID_ROUTES = {"short_circuit", "medium", "complex", "llm_needed"}

INTENT_TO_ROUTE = {
    "exact_lookup": "short_circuit",
    "attribute_lookup": "short_circuit",
    "filtered_search": "medium",
    "admissions_process": "medium",
    "cost_financial_aid": "medium",
    "career_outcomes": "medium",
    "b2b_partnership": "medium",
    "profile_management": "medium",
    "multi_constraint": "complex",
    "comparison": "complex",
    "recommendation": "complex",
    "strategy": "complex",
    "analytics_request": "complex",
    "rewrite_needed": "complex",
    "advisory": "llm_needed",
    "emotional_advisory": "llm_needed",
    "reflective_advisory": "llm_needed",
    "campus_life_fit": "llm_needed",
}


def slugify(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_query(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\s+", " ", text)
    return text


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {slugify(c): c for c in df.columns}
    for candidate in candidates:
        key = slugify(candidate)
        if key in lookup:
            return lookup[key]
    return None


def load_sources(data_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(data_dir.glob("*.csv")):
        df = pd.read_csv(path)
        q_col = find_col(df, ["Query", "query_text", "question"])
        i_col = find_col(df, ["Intent", "intent_label"])
        c_col = find_col(df, ["Complexity", "route", "routing_tier"])
        p_col = find_col(df, ["Persona", "persona_label"])

        if q_col is None or c_col is None:
            raise ValueError(f"{path.name}: could not find required Query/Complexity columns")

        out = pd.DataFrame({
            "query_text": df[q_col],
            "intent_raw": df[i_col] if i_col else "",
            "complexity_raw": df[c_col],
            "persona_raw": df[p_col] if p_col else "",
        })
        out["source_file"] = path.name
        out["source_row"] = range(2, len(out) + 2)
        frames.append(out)

    if not frames:
        raise ValueError(f"No CSV files found in {data_dir}")

    raw = pd.concat(frames, ignore_index=True)
    raw["query_text"] = raw["query_text"].fillna("").astype(str).str.strip()
    raw["query_norm"] = raw["query_text"].map(normalize_query)
    raw["intent"] = raw["intent_raw"].map(slugify)
    raw["observed_route"] = raw["complexity_raw"].map(slugify)
    raw["persona"] = raw["persona_raw"].map(slugify)

    raw = raw.loc[raw["query_norm"].ne("")].copy()
    raw = raw.loc[~raw["query_norm"].isin({"query", "query_text", "question"})].copy()
    return raw.reset_index(drop=True)


def choose_resolution(group: pd.DataFrame) -> dict[str, object]:
    valid_obs = [x for x in group["observed_route"] if x in VALID_ROUTES]
    obs_counts = Counter(valid_obs)

    mapped_routes = [INTENT_TO_ROUTE[x] for x in group["intent"] if x in INTENT_TO_ROUTE]
    mapped_counts = Counter(mapped_routes)

    # Rule 1: intent metadata unanimously maps to a single route.
    if mapped_counts and len(mapped_counts) == 1:
        route = next(iter(mapped_counts))
        return {
            "resolved_route": route,
            "resolution_method": "intent_policy",
            "resolution_confidence": 1.0,
        }

    # Rule 2: strong majority of observed valid labels.
    if obs_counts:
        ranked = obs_counts.most_common()
        top_label, top_n = ranked[0]
        second_n = ranked[1][1] if len(ranked) > 1 else 0
        total = sum(obs_counts.values())
        share = top_n / total
        margin = top_n - second_n
        if share >= 0.67 and margin >= 2:
            return {
                "resolved_route": top_label,
                "resolution_method": "strong_majority",
                "resolution_confidence": round(share, 6),
            }

    return {
        "resolved_route": "",
        "resolution_method": "manual_review",
        "resolution_confidence": 0.0,
    }


def build_resolution_table(raw: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for query_norm, group in raw.groupby("query_norm", sort=True):
        resolution = choose_resolution(group)
        obs_counts = Counter(x for x in group["observed_route"] if x)
        intent_counts = Counter(x for x in group["intent"] if x)
        persona_counts = Counter(x for x in group["persona"] if x)

        representative = group.iloc[0]["query_text"]
        records.append({
            "query_text": representative,
            "query_norm": query_norm,
            "resolved_route": resolution["resolved_route"],
            "resolution_method": resolution["resolution_method"],
            "resolution_confidence": resolution["resolution_confidence"],
            "row_count": len(group),
            "observed_routes": "|".join(f"{k}:{v}" for k, v in sorted(obs_counts.items())),
            "observed_intents": "|".join(f"{k}:{v}" for k, v in sorted(intent_counts.items())),
            "observed_personas": "|".join(f"{k}:{v}" for k, v in sorted(persona_counts.items())),
            "source_files": "|".join(sorted(set(group["source_file"]))),
        })

    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Query Intent Resolver V1 routing-label conflicts")
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory containing raw CSV files")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for cleaned outputs")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = load_sources(args.data_dir)
    resolution = build_resolution_table(raw)

    manual = resolution.loc[resolution["resolution_method"].eq("manual_review")].copy()
    cleaned = resolution.loc[resolution["resolved_route"].isin(VALID_ROUTES), [
        "query_text",
        "resolved_route",
        "resolution_method",
        "resolution_confidence",
        "row_count",
    ]].rename(columns={"resolved_route": "route"})

    # One row per normalized exact query. V1 is query-only, so retaining repeated exact
    # strings would overweight template duplicates and can leak them across splits.
    cleaned = cleaned.reset_index(drop=True)

    raw.to_csv(args.output_dir / "raw_normalized_rows.csv", index=False)
    resolution.to_csv(args.output_dir / "query_resolution_audit.csv", index=False)
    manual.to_csv(args.output_dir / "manual_review_queue.csv", index=False)
    cleaned.to_csv(args.output_dir / "cleaned_unique_queries.csv", index=False)

    summary = {
        "raw_rows": int(len(raw)),
        "unique_normalized_queries": int(len(resolution)),
        "resolved_unique_queries": int(len(cleaned)),
        "manual_review_unique_queries": int(len(manual)),
        "manual_review_share": round(len(manual) / max(len(resolution), 1), 6),
        "resolution_methods": {k: int(v) for k, v in resolution["resolution_method"].value_counts().to_dict().items()},
        "resolved_route_distribution": {k: int(v) for k, v in cleaned["route"].value_counts().to_dict().items()},
        "valid_routes": sorted(VALID_ROUTES),
    }
    (args.output_dir / "cleanup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

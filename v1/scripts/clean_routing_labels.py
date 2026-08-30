from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def slugify(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_query(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    text = text.translate(
        str.maketrans(
            {
                "’": "'",
                "‘": "'",
                "“": '"',
                "”": '"',
                "–": "-",
                "—": "-",
                "−": "-",
                "\u00a0": " ",
            }
        )
    )
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\s\?\!\.,;:]+|[\s\?\!\.,;:]+$", "", text)
    return text


def stable_query_id(query_norm: str) -> str:
    return hashlib.sha256(query_norm.encode("utf-8")).hexdigest()[:16]


def find_col(df: pd.DataFrame, candidates: list[str], *, exclude: set[str] | None = None) -> str | None:
    excluded = exclude or set()
    lookup = {slugify(column): column for column in df.columns if column not in excluded}
    for candidate in candidates:
        key = slugify(candidate)
        if key in lookup:
            return lookup[key]
    return None


def read_csv_robust(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, on_bad_lines="skip")
        except Exception as exc:  # pragma: no cover - malformed external file fallback
            last_error = exc
    raise ValueError(f"Could not read {path}: {last_error}")


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_overrides(path: Path | None, valid_routes: set[str]) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    frame = read_csv_robust(path)
    query_col = find_col(frame, ["query_text", "query"])
    route_col = find_col(frame, ["route", "complexity"])
    rationale_col = find_col(frame, ["rationale", "notes"])
    if query_col is None or route_col is None:
        raise ValueError("Override file must contain query_text and route columns")

    overrides: dict[str, dict[str, str]] = {}
    for _, row in frame.iterrows():
        query_norm = normalize_query(row[query_col])
        route = slugify(row[route_col])
        if not query_norm:
            continue
        if route not in valid_routes:
            raise ValueError(f"Invalid override route {route!r} for {query_norm!r}")
        if query_norm in overrides and overrides[query_norm]["route"] != route:
            raise ValueError(f"Conflicting override entries for {query_norm!r}")
        overrides[query_norm] = {
            "route": route,
            "rationale": str(row[rationale_col]).strip() if rationale_col else "manual override",
        }
    return overrides


def load_sources(data_dir: Path, policy: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    manifest: list[dict[str, Any]] = []
    label_aliases = {slugify(key): value for key, value in policy.get("label_aliases", {}).items()}
    pipeline_to_route = {
        slugify(key): value for key, value in policy.get("pipeline_to_route", {}).items()
    }

    for path in sorted(data_dir.glob("*.csv")):
        frame = read_csv_robust(path)
        query_col = find_col(frame, ["Query", "query_text", "question"])
        intent_col = find_col(frame, ["Intent", "intent_label"])
        complexity_col = find_col(frame, ["Complexity", "complexity_label", "routing_tier", "route"])
        persona_col = find_col(frame, ["Persona", "persona_label"])
        pipeline_col = find_col(
            frame,
            ["Route", "expected_pipeline", "pipeline", "routing_hint", "path"],
            exclude={complexity_col} if complexity_col else set(),
        )
        entities_col = find_col(frame, ["Entities", "entities_json", "entities"])
        notes_col = find_col(frame, ["Notes", "notes", "rationale"])
        if query_col is None or complexity_col is None:
            raise ValueError(f"{path.name}: required Query/Complexity columns were not found")

        out = pd.DataFrame(
            {
                "query_text": frame[query_col],
                "intent_raw": frame[intent_col] if intent_col else "",
                "complexity_raw": frame[complexity_col],
                "persona_raw": frame[persona_col] if persona_col else "",
                "pipeline_raw": frame[pipeline_col] if pipeline_col else "",
                "entities_raw": frame[entities_col] if entities_col else "",
                "notes_raw": frame[notes_col] if notes_col else "",
            }
        )
        out["source_file"] = path.name
        out["source_row"] = range(2, len(out) + 2)
        frames.append(out)
        manifest.append(
            {
                "file": path.name,
                "rows_read": int(len(out)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    if not frames:
        raise ValueError(f"No CSV files found in {data_dir}")

    raw = pd.concat(frames, ignore_index=True)
    raw["query_text"] = raw["query_text"].fillna("").astype(str).str.strip()
    raw["query_norm"] = raw["query_text"].map(normalize_query)
    raw["query_id"] = raw["query_norm"].map(stable_query_id)
    raw["intent"] = raw["intent_raw"].map(slugify)
    raw["persona"] = raw["persona_raw"].map(slugify)
    raw["observed_route_raw"] = raw["complexity_raw"].map(slugify)
    raw["observed_route"] = raw["observed_route_raw"].map(lambda value: label_aliases.get(value, value))
    raw["pipeline"] = raw["pipeline_raw"].map(slugify)
    raw["pipeline_route"] = raw["pipeline"].map(pipeline_to_route).fillna("")

    header_values = {"query", "query_text", "question"}
    raw = raw.loc[raw["query_norm"].ne("") & ~raw["query_norm"].isin(header_values)].copy()
    return raw.reset_index(drop=True), manifest


def _strong_majority(
    counts: Counter[str],
    *,
    min_share: float,
    min_margin: int,
) -> tuple[str, float] | None:
    if not counts:
        return None
    ranked = counts.most_common()
    top_label, top_count = ranked[0]
    second_count = ranked[1][1] if len(ranked) > 1 else 0
    total = sum(counts.values())
    share = top_count / total
    if share >= min_share and top_count - second_count >= min_margin:
        return top_label, share
    return None


def choose_resolution(
    group: pd.DataFrame,
    *,
    valid_routes: set[str],
    intent_to_route: dict[str, str],
    overrides: dict[str, dict[str, str]],
    cleanup_policy: dict[str, Any] | None = None,
) -> dict[str, object]:
    settings = cleanup_policy or {}
    query_norm = str(group.iloc[0]["query_norm"])
    if query_norm in overrides:
        override = overrides[query_norm]
        return {
            "resolved_route": override["route"],
            "resolution_method": "manual_override",
            "resolution_confidence": 1.0,
            "resolution_note": override["rationale"],
        }

    valid_observed = [value for value in group["observed_route"] if value in valid_routes]
    observed_counts = Counter(valid_observed)
    mapped_intents = [intent_to_route[value] for value in group["intent"] if value in intent_to_route]
    intent_counts = Counter(mapped_intents)
    mapped_pipelines = [value for value in group.get("pipeline_route", pd.Series(dtype=str)) if value in valid_routes]
    pipeline_counts = Counter(mapped_pipelines)

    intent_coverage = len(mapped_intents) / max(len(group), 1)
    if len(intent_counts) == 1 and intent_coverage >= float(settings.get("intent_policy_min_coverage", 0.8)):
        route = next(iter(intent_counts))
        return {
            "resolved_route": route,
            "resolution_method": "intent_policy",
            "resolution_confidence": round(max(0.85, min(0.98, intent_coverage)), 6),
            "resolution_note": "Recognized intents consistently map to one frozen V1 route",
        }

    pipeline_coverage = len(mapped_pipelines) / max(len(group), 1)
    if len(pipeline_counts) == 1 and pipeline_coverage >= float(settings.get("pipeline_policy_min_coverage", 0.8)):
        route = next(iter(pipeline_counts))
        return {
            "resolved_route": route,
            "resolution_method": "pipeline_policy",
            "resolution_confidence": round(max(0.85, min(0.98, pipeline_coverage)), 6),
            "resolution_note": "Historical pipeline values consistently map to one frozen V1 route",
        }

    if len(observed_counts) == 1:
        route = next(iter(observed_counts))
        return {
            "resolved_route": route,
            "resolution_method": "unanimous_observed",
            "resolution_confidence": 1.0,
            "resolution_note": "All valid historical route labels agree",
        }

    observed_majority = _strong_majority(
        observed_counts,
        min_share=float(settings.get("observed_majority_min_share", 0.67)),
        min_margin=int(settings.get("observed_majority_min_margin", 2)),
    )
    if observed_majority:
        route, share = observed_majority
        return {
            "resolved_route": route,
            "resolution_method": "strong_observed_majority",
            "resolution_confidence": round(share, 6),
            "resolution_note": f"Observed route majority {observed_counts[route]}/{sum(observed_counts.values())}",
        }

    intent_majority = _strong_majority(
        intent_counts,
        min_share=float(settings.get("intent_majority_min_share", 0.75)),
        min_margin=int(settings.get("intent_majority_min_margin", 2)),
    )
    if intent_majority:
        route, share = intent_majority
        return {
            "resolved_route": route,
            "resolution_method": "strong_intent_majority",
            "resolution_confidence": round(share * 0.95, 6),
            "resolution_note": f"Mapped intent majority {intent_counts[route]}/{sum(intent_counts.values())}",
        }

    suggestions = Counter()
    suggestions.update(observed_counts)
    suggestions.update(intent_counts)
    suggestions.update(pipeline_counts)
    suggested_route, suggested_count = suggestions.most_common(1)[0] if suggestions else ("", 0)
    suggestion_total = sum(suggestions.values())
    return {
        "resolved_route": "",
        "resolution_method": "manual_review",
        "resolution_confidence": 0.0,
        "resolution_note": "Evidence was tied, weak, missing, or internally inconsistent",
        "suggested_route": suggested_route,
        "suggested_confidence": round(suggested_count / suggestion_total, 6) if suggestion_total else 0.0,
    }


def counter_string(values: pd.Series, valid_only: set[str] | None = None) -> str:
    cleaned = [value for value in values if value and (valid_only is None or value in valid_only)]
    return "|".join(f"{key}:{count}" for key, count in sorted(Counter(cleaned).items()))


def mode_value(values: pd.Series) -> str:
    cleaned = [str(value) for value in values if str(value)]
    return Counter(cleaned).most_common(1)[0][0] if cleaned else ""


def build_resolution_table(
    raw: pd.DataFrame,
    *,
    valid_routes: set[str],
    intent_to_route: dict[str, str],
    overrides: dict[str, dict[str, str]],
    cleanup_policy: dict[str, Any] | None = None,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for query_norm, group in raw.groupby("query_norm", sort=True):
        resolution = choose_resolution(
            group,
            valid_routes=valid_routes,
            intent_to_route=intent_to_route,
            overrides=overrides,
            cleanup_policy=cleanup_policy,
        )
        representative = sorted(
            group["query_text"].astype(str).tolist(), key=lambda value: (len(value), value.casefold())
        )[0]
        records.append(
            {
                "query_id": stable_query_id(query_norm),
                "query_text": representative,
                "query_norm": query_norm,
                "resolved_route": resolution["resolved_route"],
                "resolution_method": resolution["resolution_method"],
                "resolution_confidence": resolution["resolution_confidence"],
                "resolution_note": resolution["resolution_note"],
                "suggested_route": resolution.get("suggested_route", ""),
                "suggested_confidence": resolution.get("suggested_confidence", 0.0),
                "row_count": int(len(group)),
                "observed_routes": counter_string(group["observed_route"]),
                "observed_valid_routes": counter_string(group["observed_route"], valid_routes),
                "observed_pipeline_routes": counter_string(group["pipeline_route"], valid_routes),
                "canonical_intent": mode_value(group["intent"]),
                "persona_hint": mode_value(group["persona"]),
                "observed_intents": counter_string(group["intent"]),
                "observed_personas": counter_string(group["persona"]),
                "source_files": "|".join(sorted(set(group["source_file"].astype(str)))),
                "source_rows": "|".join(
                    f"{row.source_file}:{row.source_row}" for row in group.itertuples()
                ),
            }
        )
    return pd.DataFrame(records)


def run_cleanup(
    *,
    data_dir: Path,
    output_dir: Path,
    policy_path: Path,
    overrides_path: Path | None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    policy = load_policy(policy_path)
    valid_routes = set(policy["valid_routes"])
    overrides = load_overrides(overrides_path, valid_routes)
    raw, source_manifest = load_sources(data_dir, policy)
    resolution = build_resolution_table(
        raw,
        valid_routes=valid_routes,
        intent_to_route=policy["intent_to_route"],
        overrides=overrides,
        cleanup_policy=policy.get("cleanup", {}),
    )

    manual = resolution.loc[resolution["resolution_method"].eq("manual_review")].copy()
    manual["review_route"] = ""
    manual["reviewer"] = ""
    manual["review_notes"] = ""
    cleaned = resolution.loc[resolution["resolved_route"].isin(valid_routes)].copy()
    cleaned = cleaned.rename(columns={"resolved_route": "route"}).reset_index(drop=True)
    invalid_rows = raw.loc[~raw["observed_route"].isin(valid_routes)].copy()
    conflict_queries = resolution.loc[resolution["observed_valid_routes"].str.count(r"\|").ge(1)].copy()

    raw.to_csv(output_dir / "raw_normalized_rows.csv", index=False)
    resolution.to_csv(output_dir / "query_resolution_audit.csv", index=False)
    manual.to_csv(output_dir / "manual_review_queue.csv", index=False)
    cleaned.to_csv(output_dir / "cleaned_unique_queries.csv", index=False)
    invalid_rows.to_csv(output_dir / "invalid_label_rows.csv", index=False)
    conflict_queries.to_csv(output_dir / "conflicting_query_audit.csv", index=False)

    summary: dict[str, Any] = {
        "pipeline_version": "1.0.0",
        "raw_rows": int(len(raw)),
        "source_files": source_manifest,
        "unique_normalized_queries": int(len(resolution)),
        "resolved_unique_queries": int(len(cleaned)),
        "manual_review_unique_queries": int(len(manual)),
        "manual_review_share": round(len(manual) / max(len(resolution), 1), 6),
        "conflicting_unique_queries_before_resolution": int(len(conflict_queries)),
        "invalid_route_rows": int(len(invalid_rows)),
        "manual_overrides_loaded": int(len(overrides)),
        "resolution_methods": {
            key: int(value) for key, value in resolution["resolution_method"].value_counts().to_dict().items()
        },
        "resolved_route_distribution": {
            key: int(value) for key, value in cleaned["route"].value_counts().to_dict().items()
        },
        "valid_routes": sorted(valid_routes),
    }
    (output_dir / "cleanup_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Query Intent Resolver V1 route-label conflicts")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path("v1/config/route_policy.json"))
    parser.add_argument("--overrides", type=Path, default=Path("v1/data/manual_overrides.csv"))
    args = parser.parse_args()
    summary = run_cleanup(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        policy_path=args.policy,
        overrides_path=args.overrides,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

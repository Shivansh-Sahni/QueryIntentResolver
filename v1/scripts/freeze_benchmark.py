from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROUTES = ["short_circuit", "medium", "complex", "llm_needed"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_key(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def allocate_counts(
    counts: dict[str, int],
    size: int,
    min_per_class: int,
    max_class_fraction: float,
) -> dict[str, int]:
    if size <= 0:
        raise ValueError("Benchmark size must be positive")
    if sum(counts.values()) <= size:
        raise ValueError("Benchmark size must be smaller than the eligible cleaned dataset")
    missing = [route for route in ROUTES if counts.get(route, 0) < min_per_class]
    if missing:
        raise ValueError(
            f"Not enough high-trust examples for {missing}; need at least {min_per_class} per route. Counts: {counts}"
        )

    base = size // len(ROUTES)
    caps = {
        route: min(counts[route] - 1, max(min_per_class, int(counts[route] * max_class_fraction)))
        for route in ROUTES
    }
    if sum(caps.values()) < size:
        caps = {route: counts[route] - 1 for route in ROUTES}

    allocation = {route: min(base, caps[route]) for route in ROUTES}
    remainder = size - sum(allocation.values())
    while remainder:
        progressed = False
        for route in ROUTES:
            if allocation[route] < caps[route]:
                allocation[route] += 1
                remainder -= 1
                progressed = True
                if remainder == 0:
                    break
        if not progressed:
            raise RuntimeError("Unable to allocate benchmark rows while preserving training examples")
    return allocation


def _load_cleaned(cleaned_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(cleaned_path, dtype=str, keep_default_na=False)
    required = {
        "query_id",
        "query_text",
        "query_norm",
        "route",
        "resolution_confidence",
        "resolution_method",
    }
    if missing := required - set(frame.columns):
        raise ValueError(f"Cleaned dataset is missing columns: {sorted(missing)}")
    frame["resolution_confidence"] = pd.to_numeric(
        frame["resolution_confidence"], errors="coerce"
    ).fillna(0.0)
    frame = frame.loc[frame["route"].isin(ROUTES)].copy()
    frame = frame.drop_duplicates(subset=["query_id"], keep="first").reset_index(drop=True)
    if frame["query_norm"].duplicated().any():
        raise ValueError("Duplicate normalized queries remain in cleaned input")
    return frame


def _write_current_training(
    *,
    cleaned: pd.DataFrame,
    benchmark: pd.DataFrame,
    cleaned_path: Path,
    output_dir: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    benchmark_ids = set(benchmark["query_id"])
    training = cleaned.loc[~cleaned["query_id"].isin(benchmark_ids)].copy()
    training = training.sort_values("query_id").reset_index(drop=True)

    overlap_ids = set(training["query_id"]) & benchmark_ids
    overlap_queries = set(training["query_norm"]) & set(benchmark["query_norm"])
    if overlap_ids or overlap_queries:
        raise RuntimeError(
            f"Leakage detected: {len(overlap_ids)} IDs and {len(overlap_queries)} normalized queries overlap"
        )

    training_path = output_dir / "training_clean.csv"
    training.to_csv(training_path, index=False)
    training_manifest = {
        "source_cleaned_file": str(cleaned_path),
        "source_cleaned_sha256": sha256_file(cleaned_path),
        "training_clean_sha256": sha256_file(training_path),
        "training_rows": int(len(training)),
        "training_route_distribution": {
            key: int(value) for key, value in training["route"].value_counts().to_dict().items()
        },
        "benchmark_rows_excluded": int(len(benchmark)),
        "overlap_query_ids": int(len(overlap_ids)),
        "overlap_normalized_queries": int(len(overlap_queries)),
    }
    (output_dir / "training_manifest.json").write_text(
        json.dumps(training_manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return training, training_manifest


def _validate_existing_benchmark(
    *,
    cleaned: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    manifest_path = output_dir / "benchmark_manifest.json"
    gold_path = output_dir / "benchmark_gold.csv"
    queries_path = output_dir / "benchmark_queries.csv"
    if not manifest_path.exists() or not gold_path.exists() or not queries_path.exists():
        raise FileNotFoundError("Existing benchmark is incomplete; use --force-new-version to recreate it")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("benchmark_gold_sha256") != sha256_file(gold_path):
        raise RuntimeError("Frozen benchmark hash mismatch; refusing to overwrite or reuse it")
    if manifest.get("benchmark_queries_sha256") != sha256_file(queries_path):
        raise RuntimeError("Frozen benchmark query-file hash mismatch")

    benchmark = pd.read_csv(gold_path, dtype=str, keep_default_na=False)
    required = {"benchmark_id", "query_id", "query_text", "query_norm", "route"}
    if missing := required - set(benchmark.columns):
        raise ValueError(f"Existing frozen benchmark is missing columns: {sorted(missing)}")
    if benchmark["benchmark_id"].duplicated().any() or benchmark["query_id"].duplicated().any():
        raise ValueError("Existing frozen benchmark contains duplicate IDs")

    current = cleaned.set_index("query_id")
    missing_ids = [query_id for query_id in benchmark["query_id"] if query_id not in current.index]
    if missing_ids:
        raise RuntimeError(
            f"Current cleaned dataset no longer contains {len(missing_ids)} frozen benchmark queries"
        )
    current_routes = benchmark["query_id"].map(current["route"])
    changed = benchmark.loc[current_routes.to_numpy() != benchmark["route"].to_numpy()]
    if len(changed):
        raise RuntimeError(
            f"Current cleanup policy changes {len(changed)} frozen benchmark labels. Create a new version explicitly."
        )
    return benchmark, manifest


def freeze_benchmark(
    cleaned_path: Path,
    output_dir: Path,
    *,
    benchmark_size: int = 300,
    min_per_class: int = 30,
    max_class_fraction: float = 0.25,
    seed: int = 20260830,
    min_resolution_confidence: float = 0.95,
    allowed_methods: set[str] | None = None,
    benchmark_version: str = "qir-v1.0.0",
    force_new_version: bool = False,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    allowed_methods = allowed_methods or {
        "manual_override",
        "unanimous_observed",
        "intent_policy",
        "pipeline_policy",
    }
    cleaned = _load_cleaned(cleaned_path)
    manifest_path = output_dir / "benchmark_manifest.json"

    if manifest_path.exists() and not force_new_version:
        benchmark, manifest = _validate_existing_benchmark(cleaned=cleaned, output_dir=output_dir)
        training, training_manifest = _write_current_training(
            cleaned=cleaned,
            benchmark=benchmark,
            cleaned_path=cleaned_path,
            output_dir=output_dir,
        )
        split_report = {
            "benchmark_status": "reused_immutable",
            "training_rows": int(len(training)),
            "benchmark_rows": int(len(benchmark)),
            "overlap_query_ids": 0,
            "overlap_normalized_queries": 0,
            "training_route_distribution": training_manifest["training_route_distribution"],
            "benchmark_route_distribution": {
                key: int(value) for key, value in benchmark["route"].value_counts().to_dict().items()
            },
        }
        (output_dir / "split_integrity_report.json").write_text(
            json.dumps(split_report, indent=2, sort_keys=True), encoding="utf-8"
        )
        return {**split_report, "manifest": manifest}

    eligible = cleaned.loc[
        cleaned["resolution_confidence"].ge(min_resolution_confidence)
        & cleaned["resolution_method"].isin(allowed_methods)
    ].copy()
    counts = {route: int(eligible["route"].eq(route).sum()) for route in ROUTES}
    allocation = allocate_counts(counts, benchmark_size, min_per_class, max_class_fraction)

    parts: list[pd.DataFrame] = []
    for route in ROUTES:
        group = eligible.loc[eligible["route"].eq(route)].copy()
        group["_stable_key"] = group["query_id"].map(lambda value: stable_key(seed, value))
        group = group.sort_values(["_stable_key", "query_id"]).head(allocation[route])
        parts.append(group.drop(columns=["_stable_key"]))

    benchmark = pd.concat(parts, ignore_index=True)
    benchmark["_stable_key"] = benchmark["query_id"].map(lambda value: stable_key(seed + 1, value))
    benchmark = benchmark.sort_values(["_stable_key", "query_id"]).drop(columns=["_stable_key"])
    benchmark = benchmark.reset_index(drop=True)
    benchmark.insert(0, "benchmark_id", [f"qirv1-{index:04d}" for index in range(1, len(benchmark) + 1)])

    gold_columns = [
        "benchmark_id",
        "query_id",
        "query_text",
        "query_norm",
        "route",
        "resolution_method",
        "resolution_confidence",
        "resolution_note",
        "row_count",
        "canonical_intent",
        "persona_hint",
        "observed_intents",
        "observed_personas",
        "source_files",
    ]
    gold_columns = [column for column in gold_columns if column in benchmark.columns]
    benchmark_gold = benchmark[gold_columns]

    gold_path = output_dir / "benchmark_gold.csv"
    queries_path = output_dir / "benchmark_queries.csv"
    review_path = output_dir / "benchmark_review_template.csv"
    benchmark_gold.to_csv(gold_path, index=False)
    benchmark[["benchmark_id", "query_id", "query_text"]].to_csv(queries_path, index=False)

    review = benchmark_gold.copy()
    review["review_status"] = "pending"
    review["reviewer"] = ""
    review["review_route"] = ""
    review["review_notes"] = ""
    review.to_csv(review_path, index=False)

    manifest = {
        "benchmark_version": benchmark_version,
        "status": "frozen_immutable",
        "created_by": "v1/scripts/freeze_benchmark.py",
        "seed": seed,
        "benchmark_size": int(len(benchmark_gold)),
        "benchmark_rows": int(len(benchmark_gold)),
        "minimum_resolution_confidence": min_resolution_confidence,
        "allowed_resolution_methods": sorted(allowed_methods),
        "maximum_fraction_taken_from_any_route": max_class_fraction,
        "initial_source_cleaned_file": str(cleaned_path),
        "initial_source_cleaned_sha256": sha256_file(cleaned_path),
        "benchmark_gold_sha256": sha256_file(gold_path),
        "benchmark_queries_sha256": sha256_file(queries_path),
        "route_order": ROUTES,
        "allocation": allocation,
        "leakage_check": "passed",
        "freeze_rule": (
            "Do not tune against, relabel, replace, or regenerate benchmark_gold.csv. "
            "Accepted review changes require a new benchmark version and --force-new-version."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "FROZEN.md").write_text(
        f"# Frozen Benchmark\n\nVersion: `{benchmark_version}`\n\nSHA-256: `{manifest['benchmark_gold_sha256']}`\n",
        encoding="utf-8",
    )

    training, training_manifest = _write_current_training(
        cleaned=cleaned,
        benchmark=benchmark_gold,
        cleaned_path=cleaned_path,
        output_dir=output_dir,
    )
    split_report = {
        "benchmark_status": "created_and_frozen",
        "dataset_rows_resolved": int(len(cleaned)),
        "dataset_rows_eligible_for_benchmark": int(len(eligible)),
        "training_rows": int(len(training)),
        "benchmark_rows": int(len(benchmark_gold)),
        "overlap_query_ids": 0,
        "overlap_normalized_queries": 0,
        "training_route_distribution": training_manifest["training_route_distribution"],
        "benchmark_route_distribution": {
            key: int(value) for key, value in benchmark_gold["route"].value_counts().to_dict().items()
        },
        "benchmark_allocation": allocation,
    }
    (output_dir / "split_integrity_report.json").write_text(
        json.dumps(split_report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {**split_report, "manifest": manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or safely reuse the frozen V1 benchmark")
    parser.add_argument("--cleaned", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--benchmark-size", type=int, default=300)
    parser.add_argument("--min-per-class", type=int, default=30)
    parser.add_argument("--max-class-fraction", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--min-resolution-confidence", type=float, default=0.95)
    parser.add_argument(
        "--allowed-methods",
        nargs="+",
        default=["manual_override", "unanimous_observed", "intent_policy", "pipeline_policy"],
    )
    parser.add_argument("--benchmark-version", default="qir-v1.0.0")
    parser.add_argument("--force-new-version", action="store_true")
    args = parser.parse_args()

    result = freeze_benchmark(
        args.cleaned,
        args.output_dir,
        benchmark_size=args.benchmark_size,
        min_per_class=args.min_per_class,
        max_class_fraction=args.max_class_fraction,
        seed=args.seed,
        min_resolution_confidence=args.min_resolution_confidence,
        allowed_methods=set(args.allowed_methods),
        benchmark_version=args.benchmark_version,
        force_new_version=args.force_new_version,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

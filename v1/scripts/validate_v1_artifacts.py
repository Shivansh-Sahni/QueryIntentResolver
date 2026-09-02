from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
V1_ROOT = SCRIPT_DIR.parent
SRC_DIR = V1_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qir_v1.resolver import QueryIntentResolver  # noqa: E402

VALID_ROUTES = {"short_circuit", "medium", "complex", "llm_needed"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Query Intent Resolver V1 artifacts")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("v1/artifacts"))
    args = parser.parse_args()

    root = args.artifacts_dir
    cleanup = root / "data_cleanup"
    benchmark_dir = root / "benchmark"
    models = root / "models"
    linearsvc = models / "linearsvc"
    shootout = root / "shootout"
    release = root / "release"
    required = [
        cleanup / "cleaned_unique_queries.csv",
        cleanup / "query_resolution_audit.csv",
        cleanup / "manual_review_queue.csv",
        cleanup / "cleanup_summary.json",
        cleanup / "conflicting_query_audit.csv",
        cleanup / "invalid_label_rows.csv",
        benchmark_dir / "benchmark_gold.csv",
        benchmark_dir / "benchmark_queries.csv",
        benchmark_dir / "training_clean.csv",
        benchmark_dir / "benchmark_manifest.json",
        benchmark_dir / "training_manifest.json",
        benchmark_dir / "split_integrity_report.json",
        benchmark_dir / "qwen_benchmark_input.csv",
        linearsvc / "model.joblib",
        linearsvc / "metrics.json",
        linearsvc / "predictions.csv",
        shootout / "winner.json",
        shootout / "shootout_summary.csv",
        shootout / "SHOOTOUT_REPORT.md",
        release / "model.joblib",
        release / "release_manifest.json",
        release / "sample_outputs.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required V1 artifacts: {missing}")

    cleaned = pd.read_csv(cleanup / "cleaned_unique_queries.csv", dtype=str, keep_default_na=False)
    manual = pd.read_csv(cleanup / "manual_review_queue.csv", dtype=str, keep_default_na=False)
    training = pd.read_csv(benchmark_dir / "training_clean.csv", dtype=str, keep_default_na=False)
    benchmark = pd.read_csv(benchmark_dir / "benchmark_gold.csv", dtype=str, keep_default_na=False)
    qwen_input = pd.read_csv(benchmark_dir / "qwen_benchmark_input.csv", dtype=str, keep_default_na=False)

    for name, frame in (("cleaned", cleaned), ("training", training), ("benchmark", benchmark)):
        if "query_norm" not in frame.columns or frame["query_norm"].duplicated().any():
            raise AssertionError(f"{name} has missing or duplicate normalized query keys")
        invalid = set(frame["route"]) - VALID_ROUTES
        if invalid:
            raise AssertionError(f"{name} contains invalid routes: {sorted(invalid)}")

    if set(cleaned["query_norm"]) & set(manual.get("query_norm", pd.Series(dtype=str))):
        raise AssertionError("Manual-review queries leaked into the cleaned dataset")
    if set(training["query_norm"]) & set(benchmark["query_norm"]):
        raise AssertionError("Training/benchmark normalized-query leakage detected")
    if set(training["query_id"]) & set(benchmark["query_id"]):
        raise AssertionError("Training/benchmark query-ID leakage detected")
    if benchmark["benchmark_id"].duplicated().any():
        raise AssertionError("Frozen benchmark IDs are not unique")
    if any(int(benchmark["route"].eq(route).sum()) == 0 for route in VALID_ROUTES):
        raise AssertionError("Frozen benchmark does not cover all four routes")
    if set(qwen_input["benchmark_id"]) != set(benchmark["benchmark_id"]):
        raise AssertionError("Qwen input IDs do not match the frozen benchmark")
    if {"route", "true_route", "gold_route"} & set(qwen_input.columns):
        raise AssertionError("Qwen input leaks gold route labels")

    benchmark_manifest = json.loads((benchmark_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))
    if benchmark_manifest["benchmark_gold_sha256"] != sha256_file(benchmark_dir / "benchmark_gold.csv"):
        raise AssertionError("Frozen benchmark hash mismatch")
    if benchmark_manifest["benchmark_queries_sha256"] != sha256_file(benchmark_dir / "benchmark_queries.csv"):
        raise AssertionError("Frozen benchmark query-file hash mismatch")
    if int(benchmark_manifest.get("benchmark_rows", benchmark_manifest["benchmark_size"])) != len(benchmark):
        raise AssertionError("Frozen benchmark manifest row count mismatch")

    training_manifest = json.loads((benchmark_dir / "training_manifest.json").read_text(encoding="utf-8"))
    if training_manifest["training_clean_sha256"] != sha256_file(benchmark_dir / "training_clean.csv"):
        raise AssertionError("Training pool hash mismatch")
    if int(training_manifest["training_rows"]) != len(training):
        raise AssertionError("Training manifest row count mismatch")

    verified_real_models: list[str] = []
    for metrics_path in sorted(models.rglob("metrics.json")):
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics.get("model_status") != "real":
            continue
        if metrics.get("benchmark_sha256") != benchmark_manifest["benchmark_gold_sha256"]:
            raise AssertionError(f"Model metrics are not tied to the frozen benchmark: {metrics_path}")
        if int(metrics.get("benchmark_rows", -1)) != len(benchmark):
            raise AssertionError(f"Model benchmark row count mismatch: {metrics_path}")
        if float(metrics.get("coverage", 0.0)) != 1.0:
            raise AssertionError(f"Model prediction coverage is incomplete: {metrics_path}")
        verified_real_models.append(str(metrics_path.relative_to(root)))

    shootout_winner = json.loads((shootout / "winner.json").read_text(encoding="utf-8"))
    if shootout_winner.get("benchmark_sha256") != benchmark_manifest["benchmark_gold_sha256"]:
        raise AssertionError("Shootout is not bound to the frozen benchmark hash")

    recommended = shootout_winner.get("recommended_model", shootout_winner.get("winner", {}))
    analytical_leader = shootout_winner.get("leaderboard_leader", recommended)
    if not recommended.get("model_name"):
        raise AssertionError("Shootout did not select a recommended model")
    if recommended.get("model_status") != "real":
        raise AssertionError("A diagnostic or unverified model was selected as the recommended release model")
    if recommended.get("benchmark_verified") is not True:
        raise AssertionError("Recommended model is not verified against the frozen benchmark")
    if float(recommended.get("coverage", 0.0)) != 1.0:
        raise AssertionError("Recommended model does not cover the complete frozen benchmark")

    release_manifest = json.loads((release / "release_manifest.json").read_text(encoding="utf-8"))
    hashes = release_manifest["hashes"]
    if hashes["model_sha256"] != sha256_file(release / "model.joblib"):
        raise AssertionError("Release model hash mismatch")
    if hashes["benchmark_sha256"] != sha256_file(benchmark_dir / "benchmark_gold.csv"):
        raise AssertionError("Release benchmark hash mismatch")
    if hashes["training_sha256"] != sha256_file(benchmark_dir / "training_clean.csv"):
        raise AssertionError("Release training hash mismatch")
    if hashes["policy_sha256"] != sha256_file(V1_ROOT / "config" / "route_policy.json"):
        raise AssertionError("Release policy hash mismatch")
    if release_manifest.get("recommended_model") != recommended.get("model_name"):
        raise AssertionError("Release manifest does not match the shootout recommendation")
    if release_manifest.get("packaged_model") != recommended.get("model_name"):
        raise AssertionError("Packaged model differs from the recommended model")

    resolver = QueryIntentResolver(
        model_path=release / "model.joblib",
        policy_path=V1_ROOT / "config" / "route_policy.json",
    )
    smoke_queries = [
        "MIT",
        "UCLA tuition",
        "colleges in California",
        "UCLA vs USC for engineering",
        "schools with normal people",
    ]
    outputs = [resolver.resolve(query) for query in smoke_queries]
    for output in outputs:
        if set(output) != {"route", "confidence"}:
            raise AssertionError(f"Runtime output violates V1 contract: {output}")
        if output["route"] not in VALID_ROUTES or not 0.0 <= float(output["confidence"]) <= 1.0:
            raise AssertionError(f"Invalid runtime output: {output}")

    debug = resolver.resolve(
        "colleges in California",
        persona="parent",
        page="search",
        filters={"state": "CA"},
        context=[{"role": "user", "content": "prior"}],
        session={"id": "test"},
        include_optional_fields=True,
    )
    if debug.get("context_used") is not False:
        raise AssertionError("Optional context is not decoupled in V1")

    report = {
        "schema_version": "1.0.1",
        "status": "passed",
        "cleaned_unique_queries": int(len(cleaned)),
        "manual_review_unique_queries": int(len(manual)),
        "training_rows": int(len(training)),
        "benchmark_rows": int(len(benchmark)),
        "benchmark_distribution": {
            route: int(benchmark["route"].eq(route).sum()) for route in sorted(VALID_ROUTES)
        },
        "training_benchmark_exact_query_leakage": 0,
        "manual_review_training_leakage": 0,
        "verified_real_model_metrics": verified_real_models,
        "frozen_hashes_verified": True,
        "release_hashes_verified": True,
        "runtime_contract_verified": True,
        "optional_context_decoupling_verified": True,
        "qwen_input_gold_label_leakage": False,
        "recommended_model": recommended["model_name"],
        "analytical_score_leader": analytical_leader.get("model_name"),
        "diagnostic_model_packaging_blocked": True,
        "smoke_outputs": [
            {"query_text": query, **output} for query, output in zip(smoke_queries, outputs)
        ],
    }
    (root / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

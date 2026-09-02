from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
V1_ROOT = SCRIPT_DIR.parent
SRC_DIR = V1_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qir_v1.resolver import QueryIntentResolver  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the current Query Intent Resolver V1 release")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("v1/artifacts"))
    parser.add_argument("--policy", type=Path, default=V1_ROOT / "config" / "route_policy.json")
    args = parser.parse_args()

    root = args.artifacts_dir
    benchmark_dir = root / "benchmark"
    cleanup_dir = root / "data_cleanup"
    models_dir = root / "models"
    linearsvc_dir = models_dir / "linearsvc"
    shootout_dir = root / "shootout"
    release_dir = root / "release"
    release_dir.mkdir(parents=True, exist_ok=True)

    winner_path = shootout_dir / "winner.json"
    if not winner_path.exists():
        raise FileNotFoundError("Run compare_models.py before finalizing the release")
    shootout = json.loads(winner_path.read_text(encoding="utf-8"))

    recommended = shootout.get("recommended_model", shootout.get("winner", {}))
    analytical_leader = shootout.get("leaderboard_leader", recommended)
    recommended_name = str(recommended["model_name"])
    analytical_leader_name = str(analytical_leader["model_name"])

    if str(recommended.get("model_status")) != "real":
        raise ValueError("The recommended release model must be a real model, not a diagnostic entry")
    if not bool(recommended.get("benchmark_verified")):
        raise ValueError("The recommended release model is not tied to the frozen benchmark")
    if float(recommended.get("coverage", 0.0)) != 1.0:
        raise ValueError("The recommended release model does not have complete benchmark coverage")

    stable_model = linearsvc_dir / "model.joblib"
    if not stable_model.exists():
        raise FileNotFoundError("The stable LinearSVC runtime artifact is missing")

    packaged_model_name = "calibrated_word_char_shape_linearsvc"
    packaging_note = "The recommended model is packaged directly."
    recommended_model_path = models_dir / recommended_name / "model.joblib"

    if recommended_name == packaged_model_name:
        selected_model = stable_model
    elif recommended_model_path.exists():
        selected_model = recommended_model_path
        packaged_model_name = recommended_name
    else:
        selected_model = stable_model
        packaging_note = (
            f"The recommended model is {recommended_name}, but it has no compatible local joblib runtime artifact; "
            "the stable calibrated LinearSVC remains packaged for the API."
        )

    shutil.copy2(selected_model, release_dir / "model.joblib")
    shutil.copy2(winner_path, release_dir / "winner.json")
    if (shootout_dir / "SHOOTOUT_REPORT.md").exists():
        shutil.copy2(shootout_dir / "SHOOTOUT_REPORT.md", release_dir / "MODEL_SHOOTOUT.md")
    if (linearsvc_dir / "MODEL_CARD.md").exists():
        shutil.copy2(linearsvc_dir / "MODEL_CARD.md", release_dir / "PACKAGED_MODEL_CARD.md")
    if (linearsvc_dir / "REPORT.md").exists():
        shutil.copy2(linearsvc_dir / "REPORT.md", release_dir / "PACKAGED_MODEL_RESULTS.md")

    resolver = QueryIntentResolver(model_path=release_dir / "model.joblib", policy_path=args.policy)
    sample_queries = [
        "MIT",
        "UCLA tuition",
        "colleges in California",
        "UCLA vs USC for engineering",
        "schools with normal people",
        "affordable engineering schools near the beach with good job placement",
    ]
    samples = [
        {
            "query_text": query,
            "response": resolver.resolve(query),
            "debug_response": resolver.resolve(query, include_optional_fields=True),
        }
        for query in sample_queries
    ]
    (release_dir / "sample_outputs.json").write_text(
        json.dumps(samples, indent=2, sort_keys=True), encoding="utf-8"
    )

    benchmark_manifest = json.loads(
        (benchmark_dir / "benchmark_manifest.json").read_text(encoding="utf-8")
    )
    training_manifest = json.loads(
        (benchmark_dir / "training_manifest.json").read_text(encoding="utf-8")
    )
    cleanup_summary = json.loads(
        (cleanup_dir / "cleanup_summary.json").read_text(encoding="utf-8")
    )

    packaged_metrics_path = linearsvc_dir / "metrics.json"
    packaged_metrics = json.loads(packaged_metrics_path.read_text(encoding="utf-8"))
    if packaged_model_name != "calibrated_word_char_shape_linearsvc":
        alternate_metrics = models_dir / packaged_model_name / "metrics.json"
        if alternate_metrics.exists():
            packaged_metrics = json.loads(alternate_metrics.read_text(encoding="utf-8"))

    release_status = (
        "implementation_ready_benchmark_selected_model"
        if shootout["status"] == "final" and recommended_name == packaged_model_name
        else "implementation_ready_provisional_model"
    )
    manifest = {
        "release_version": "qir-v1.0.1",
        "benchmark_version": benchmark_manifest.get("benchmark_version", "qir-v1.0.0"),
        "status": release_status,
        "objective": "Determine handling complexity and routing tier from raw query text.",
        "contract": {
            "required_input": {"query_text": "non-empty string"},
            "required_output": {
                "route": "short_circuit | medium | complex | llm_needed",
                "confidence": "float in [0,1]",
            },
            "optional_inputs_decoupled": ["persona", "page", "filters", "context", "session"],
            "optional_outputs_reserved": ["entities", "intent"],
        },
        "shootout_status": shootout["status"],
        "selection_basis": shootout.get("selection_basis"),
        "provisional_reason": shootout.get("provisional_reason", ""),
        "recommended_model": recommended_name,
        "analytical_score_leader": analytical_leader_name,
        "packaged_model": packaged_model_name,
        "packaging_note": packaging_note,
        "real_models_evaluated": shootout.get(
            "verified_real_models_evaluated", shootout.get("real_models_evaluated", 0)
        ),
        "packaged_model_metrics": {
            key: packaged_metrics.get(key)
            for key in (
                "accuracy",
                "macro_f1",
                "false_short_circuit_rate",
                "short_circuit_recall",
                "p95_latency_ms",
                "estimated_cost_per_1000_queries_usd",
            )
        },
        "dataset": {
            "raw_rows": cleanup_summary["raw_rows"],
            "cleaned_unique_queries": cleanup_summary["resolved_unique_queries"],
            "manual_review_unique_queries": cleanup_summary["manual_review_unique_queries"],
            "training_rows": training_manifest["training_rows"],
            "benchmark_rows": benchmark_manifest["benchmark_size"],
        },
        "hashes": {
            "model_sha256": sha256_file(release_dir / "model.joblib"),
            "benchmark_sha256": sha256_file(benchmark_dir / "benchmark_gold.csv"),
            "benchmark_manifest_sha256": sha256_file(benchmark_dir / "benchmark_manifest.json"),
            "training_sha256": sha256_file(benchmark_dir / "training_clean.csv"),
            "policy_sha256": sha256_file(args.policy),
        },
        "interfaces": {
            "python": "qir_v1.QueryIntentResolver.resolve",
            "http": "POST /v1/resolve",
            "container": "v1/Dockerfile",
        },
        "mascotgo_foundry_integration": "configurable_pending_Peter_architecture_confirmation",
    }
    (release_dir / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    (release_dir / "deployment.env.example").write_text(
        "QIR_MODEL_PATH=v1/artifacts/release/model.joblib\n"
        "QIR_POLICY_PATH=v1/config/route_policy.json\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, cwd: Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute the complete Query Intent Resolver V1 core pipeline")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-dir", type=Path, default=Path("Part 1 - Phases 6 and 7/Data"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("v1/artifacts"))
    parser.add_argument("--benchmark-size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--force-new-benchmark", action="store_true")
    parser.add_argument("--with-zero-shot", action="store_true")
    parser.add_argument("--zero-shot-model", default="typeform/distilbert-base-uncased-mnli")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_dir = args.data_dir if args.data_dir.is_absolute() else repo_root / args.data_dir
    artifacts = args.artifacts_dir if args.artifacts_dir.is_absolute() else repo_root / args.artifacts_dir
    v1 = repo_root / "v1"
    scripts = v1 / "scripts"
    policy = v1 / "config" / "route_policy.json"
    overrides = v1 / "data" / "manual_overrides.csv"

    cleanup = artifacts / "data_cleanup"
    benchmark = artifacts / "benchmark"
    models = artifacts / "models"
    linearsvc = models / "linearsvc"
    rules = models / "rules"
    zero_shot = models / "zero_shot"
    qwen = models / "qwen"
    llm = models / "llm"
    shootout = artifacts / "shootout"
    release = artifacts / "release"

    # External inference can be expensive and may be contributed through a PR.
    # Preserve the committed raw export before rebuilding generated artifacts.
    qwen_export_bytes: bytes | None = None
    for candidate in (qwen / "raw_predictions.csv", qwen / "predictions.csv"):
        if candidate.exists():
            qwen_export_bytes = candidate.read_bytes()
            break

    reset_directory(cleanup)
    reset_directory(models)
    reset_directory(shootout)
    reset_directory(release)
    benchmark.mkdir(parents=True, exist_ok=True)

    run(
        [
            sys.executable,
            str(scripts / "clean_routing_labels.py"),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(cleanup),
            "--policy",
            str(policy),
            "--overrides",
            str(overrides),
        ],
        cwd=repo_root,
    )

    freeze_command = [
        sys.executable,
        str(scripts / "freeze_benchmark.py"),
        "--cleaned",
        str(cleanup / "cleaned_unique_queries.csv"),
        "--output-dir",
        str(benchmark),
        "--benchmark-size",
        str(args.benchmark_size),
        "--seed",
        str(args.seed),
    ]
    if args.force_new_benchmark:
        freeze_command.append("--force-new-version")
    run(freeze_command, cwd=repo_root)

    run(
        [
            sys.executable,
            str(scripts / "create_qwen_input.py"),
            "--benchmark-queries",
            str(benchmark / "benchmark_queries.csv"),
            "--output",
            str(benchmark / "qwen_benchmark_input.csv"),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(scripts / "train_linearsvc_v1.py"),
            "--training-pool",
            str(benchmark / "training_clean.csv"),
            "--benchmark",
            str(benchmark / "benchmark_gold.csv"),
            "--output-dir",
            str(linearsvc),
            "--policy",
            str(policy),
        ],
        cwd=repo_root,
    )

    run(
        [
            sys.executable,
            str(scripts / "run_rules_baseline.py"),
            "--benchmark",
            str(benchmark / "benchmark_gold.csv"),
            "--output-dir",
            str(rules),
            "--policy",
            str(policy),
        ],
        cwd=repo_root,
    )

    if args.with_zero_shot:
        run(
            [
                sys.executable,
                str(scripts / "run_zero_shot_baseline.py"),
                "--benchmark",
                str(benchmark / "benchmark_gold.csv"),
                "--output-dir",
                str(zero_shot),
                "--policy",
                str(policy),
                "--model",
                args.zero_shot_model,
            ],
            cwd=repo_root,
        )
    else:
        zero_shot.mkdir(parents=True, exist_ok=True)
        (zero_shot / "PENDING.md").write_text(
            "Run the zero-shot baseline with `--with-zero-shot` or through a manual GitHub Actions dispatch.\n",
            encoding="utf-8",
        )

    qwen.mkdir(parents=True, exist_ok=True)
    if qwen_export_bytes is not None:
        raw_qwen_export = qwen / "raw_predictions.csv"
        raw_qwen_export.write_bytes(qwen_export_bytes)
        run(
            [
                sys.executable,
                str(scripts / "evaluate_predictions.py"),
                "--benchmark",
                str(benchmark / "benchmark_gold.csv"),
                "--predictions",
                str(raw_qwen_export),
                "--output-dir",
                str(qwen),
                "--model-name",
                "anthony_qwen2_5_3b_lora_intent_to_route",
                "--model-status",
                "real",
                "--policy",
                str(policy),
            ],
            cwd=repo_root,
        )
        (qwen / "EVALUATION_NOTE.md").write_text(
            "# Qwen V1 evaluation\n\n"
            "The committed raw export was scored exactly as produced by the unchanged inference pipeline. "
            "`predicted_route_raw` was treated as the model's end-to-end route output. No post-hoc intent "
            "reparsing, fuzzy intent correction, generation-parameter change, or benchmark-error tuning was applied.\n",
            encoding="utf-8",
        )
        qwen_status = "evaluated_raw_route_export"
    else:
        (qwen / "PENDING.md").write_text(
            "Run Anthony's Qwen model on `v1/artifacts/benchmark/qwen_benchmark_input.csv`, then commit its raw export.\n",
            encoding="utf-8",
        )
        qwen_status = "awaiting_gpu_export"

    llm.mkdir(parents=True, exist_ok=True)
    (llm / "PENDING.md").write_text(
        "Run the optional OpenAI-compatible lightweight LLM baseline only when provider credentials are supplied.\n",
        encoding="utf-8",
    )

    run(
        [
            sys.executable,
            str(scripts / "compare_models.py"),
            "--metrics-root",
            str(models),
            "--output-dir",
            str(shootout),
            "--benchmark-manifest",
            str(benchmark / "benchmark_manifest.json"),
            "--policy",
            str(policy),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(scripts / "finalize_release.py"),
            "--artifacts-dir",
            str(artifacts),
            "--policy",
            str(policy),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(scripts / "validate_v1_artifacts.py"),
            "--artifacts-dir",
            str(artifacts),
        ],
        cwd=repo_root,
    )

    pipeline_status = {
        "status": "complete",
        "benchmark_status": json.loads(
            (benchmark / "benchmark_manifest.json").read_text(encoding="utf-8")
        )["status"],
        "linear_model_evaluated": True,
        "diagnostic_rules_evaluated": True,
        "zero_shot_requested": args.with_zero_shot,
        "qwen_status": qwen_status,
        "llm_api_status": "optional_credentials_not_supplied",
        "release_manifest": str(release / "release_manifest.json"),
    }
    (artifacts / "PIPELINE_STATUS.json").write_text(
        json.dumps(pipeline_status, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(pipeline_status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

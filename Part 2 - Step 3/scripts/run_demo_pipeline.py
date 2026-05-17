from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full illustrative step-3 demo pipeline."
    )
    parser.add_argument(
        "--source",
        default=str(Path(__file__).resolve().parents[1] / "fixtures" / "sample_clean_dataset.csv"),
        help="Source cleaned dataset to use for the demo benchmark.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "reports" / "demo_run"),
        help="Directory for demo outputs.",
    )
    parser.add_argument(
        "--benchmark-size",
        type=int,
        default=18,
        help="Benchmark size for the illustrative run.",
    )
    parser.add_argument("--seed", type=int, default=11, help="Random seed for the mock export.")
    parser.add_argument(
        "--persona-accuracy-target",
        type=float,
        default=0.89,
        help="Approximate persona accuracy for the mock export.",
    )
    parser.add_argument(
        "--intent-accuracy-target",
        type=float,
        default=0.94,
        help="Approximate intent accuracy for the mock export.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output directory before running.",
    )
    return parser.parse_args()


def run(command: list[str], *, cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if completed.stdout.strip():
        print(completed.stdout.strip())


def main() -> None:
    args = parse_args()
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parent
    output_dir = Path(args.output_dir)
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    benchmark_dir = output_dir / "benchmark"
    predictions_path = output_dir / "mock_predictions.csv"
    evaluation_dir = output_dir / "evaluation"

    run(
        [
            sys.executable,
            str(package_root / "scripts" / "create_validation_benchmark.py"),
            "--source",
            str(Path(args.source)),
            "--output-dir",
            str(benchmark_dir),
            "--benchmark-size",
            str(args.benchmark_size),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "mock_prediction_export.py"),
            "--labels",
            str(benchmark_dir / "benchmark_gold.csv"),
            "--output",
            str(predictions_path),
            "--seed",
            str(args.seed),
            "--persona-accuracy-target",
            str(args.persona_accuracy_target),
            "--intent-accuracy-target",
            str(args.intent_accuracy_target),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(benchmark_dir / "benchmark_gold.csv"),
            "--predictions",
            str(predictions_path),
            "--output-dir",
            str(evaluation_dir),
        ],
        cwd=repo_root,
    )
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        "# Demo Run\n\n"
        "This run was generated through the standalone step-3 demo pipeline.\n\n"
        "It is illustrative only and should not be presented as real model performance.\n\n"
        "Key outputs:\n\n"
        "- `benchmark/benchmark_gold.csv`\n"
        "- `benchmark/benchmark_review_template.csv`\n"
        "- `benchmark/benchmark_summary.json`\n"
        "- `mock_predictions.csv`\n"
        "- `evaluation/evaluation_summary.json`\n"
        "- `evaluation/evaluation_report.md`\n"
        "- `evaluation/evaluation_dashboard.html`\n"
        "- `evaluation/matched_predictions_enriched.csv`\n"
        "- `evaluation/confidence_band_summary.csv`\n"
        "- `evaluation/persona_accuracy_by_slice.csv`\n"
        "- `evaluation/intent_accuracy_by_slice.csv`\n"
        "- `evaluation/top_persona_confusions.csv`\n"
        "- `evaluation/top_intent_confusions.csv`\n"
        "- `evaluation/persona_confusion_matrix.csv`\n"
        "- `evaluation/intent_confusion_matrix.csv`\n"
        "- `evaluation/route_tier_confusion_matrix.csv`\n"
        "- `evaluation/prediction_errors.csv`\n",
        encoding="utf-8",
    )
    print(f"Wrote demo package to {output_dir}")


if __name__ == "__main__":
    main()

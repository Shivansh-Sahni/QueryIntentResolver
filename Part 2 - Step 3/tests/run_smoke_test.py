from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, cwd: Path, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if expect_success and completed.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise RuntimeError(f"Command unexpectedly succeeded: {' '.join(command)}")
    return completed


def main() -> None:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parent
    temp_dir = package_root / "reports" / "smoke_test_run"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    benchmark_dir = temp_dir / "benchmark"
    evaluation_dir = temp_dir / "evaluation"
    labels_path = benchmark_dir / "benchmark_gold.csv"
    predictions_path = temp_dir / "mock_predictions.csv"

    run(
        [
            sys.executable,
            str(package_root / "scripts" / "create_validation_benchmark.py"),
            "--source",
            str(package_root / "fixtures" / "sample_clean_dataset.csv"),
            "--output-dir",
            str(benchmark_dir),
            "--benchmark-size",
            "12",
        ],
        cwd=repo_root,
    )

    run(
        [
            sys.executable,
            str(package_root / "scripts" / "mock_prediction_export.py"),
            "--labels",
            str(labels_path),
            "--output",
            str(predictions_path),
            "--seed",
            "7",
        ],
        cwd=repo_root,
    )

    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(predictions_path),
            "--output-dir",
            str(evaluation_dir),
        ],
        cwd=repo_root,
    )

    summary = json.loads((evaluation_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert summary["dataset"]["total_labels"] == 12
    assert summary["dataset"]["matched_predictions"] == 12
    assert "persona_accuracy" in summary["metrics"]
    assert "intent_accuracy" in summary["metrics"]
    assert "joint_accuracy" in summary["metrics"]
    assert "route_tier_accuracy" in summary["metrics"]
    assert "acceptance" in summary
    assert "operating_counts" in summary
    assert "routing_health" in summary
    assert summary["dataset"]["matched_by_row_id"] == 12
    assert summary["dataset"]["matched_by_query"] == 0
    for band in ["0.85-1.00", "0.65-0.84", "0.40-0.64", "<0.40"]:
        assert band in summary["confidence_bands"]
    for expected_file in [
        "prediction_errors.csv",
        "matched_predictions_enriched.csv",
        "confidence_band_summary.csv",
        "persona_accuracy_by_slice.csv",
        "intent_accuracy_by_slice.csv",
        "top_persona_confusions.csv",
        "top_intent_confusions.csv",
        "persona_confusion_matrix.csv",
        "intent_confusion_matrix.csv",
        "route_tier_confusion_matrix.csv",
    ]:
        assert (evaluation_dir / expected_file).exists()

    with predictions_path.open("r", encoding="utf-8", newline="") as csv_file:
        prediction_reader = list(csv.DictReader(csv_file))
        prediction_fields = prediction_reader[0].keys()

    query_join_predictions = predictions_path.with_name("mock_predictions_query_join.csv")
    query_fields = [field for field in prediction_fields if field != "row_id"]
    with query_join_predictions.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=query_fields)
        writer.writeheader()
        for row in prediction_reader:
            writer.writerow({field: row[field] for field in query_fields})

    query_join_dir = temp_dir / "evaluation_query_join"
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(query_join_predictions),
            "--output-dir",
            str(query_join_dir),
        ],
        cwd=repo_root,
    )
    query_join_summary = json.loads((query_join_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert query_join_summary["dataset"]["matched_predictions"] == 12
    assert query_join_summary["dataset"]["matched_by_query"] == 12

    low_conf_predictions = predictions_path.with_name("mock_predictions_low_conf.csv")
    route_dir = temp_dir / "evaluation_low_conf"
    low_conf_rows = [dict(row) for row in prediction_reader]
    low_conf_rows[0]["predicted_confidence"] = "0.31"
    with low_conf_predictions.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(prediction_fields))
        writer.writeheader()
        writer.writerows(low_conf_rows)

    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(low_conf_predictions),
            "--output-dir",
            str(route_dir),
        ],
        cwd=repo_root,
    )
    low_conf_summary = json.loads((route_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert low_conf_summary["operating_counts"]["fallback_insufficient_confidence"] >= 1

    unknown_intent_predictions = predictions_path.with_name("mock_predictions_unknown_intent.csv")
    unknown_intent_rows = [dict(row) for row in prediction_reader]
    unknown_intent_rows[1]["predicted_intent"] = "unknown_intent_for_test"
    unknown_intent_rows[1]["predicted_confidence"] = "0.91"
    with unknown_intent_predictions.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(prediction_fields))
        writer.writeheader()
        writer.writerows(unknown_intent_rows)
    unknown_intent_dir = temp_dir / "evaluation_unknown_intent"
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(unknown_intent_predictions),
            "--output-dir",
            str(unknown_intent_dir),
        ],
        cwd=repo_root,
    )
    unknown_intent_summary = json.loads(
        (unknown_intent_dir / "evaluation_summary.json").read_text(encoding="utf-8")
    )
    assert unknown_intent_summary["operating_counts"]["fallback_unknown_intent"] == 1
    assert unknown_intent_summary["routing_health"]["unknown_predicted_intent_count"] == 1

    missing_predictions = predictions_path.with_name("mock_predictions_missing_one.csv")
    with missing_predictions.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(prediction_fields))
        writer.writeheader()
        writer.writerows(prediction_reader[1:])
    missing_eval_dir = temp_dir / "evaluation_missing"
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(missing_predictions),
            "--output-dir",
            str(missing_eval_dir),
        ],
        cwd=repo_root,
    )
    missing_summary = json.loads((missing_eval_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert missing_summary["dataset"]["missing_predictions"] == 1

    malformed_predictions = predictions_path.with_name("mock_predictions_malformed.csv")
    malformed_fields = [field for field in prediction_fields if field != "predicted_intent"]
    with malformed_predictions.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=malformed_fields)
        writer.writeheader()
        for row in prediction_reader:
            writer.writerow({field: row[field] for field in malformed_fields})
    malformed_eval_dir = temp_dir / "evaluation_malformed"
    failed = run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(labels_path),
            "--predictions",
            str(malformed_predictions),
            "--output-dir",
            str(malformed_eval_dir),
        ],
        cwd=repo_root,
        expect_success=False,
    )
    assert "predicted_intent" in failed.stderr or "predicted_intent" in failed.stdout

    duplicate_source_path = temp_dir / "duplicate_source.csv"
    with duplicate_source_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["Query", "Persona", "Intent"])
        writer.writeheader()
        writer.writerows(
            [
                {"Query": "compare northeastern and bu", "Persona": "high_school_student", "Intent": "comparison"},
                {"Query": "compare northeastern and bu", "Persona": "high_school_student", "Intent": "comparison"},
                {"Query": "find colleges in chicago", "Persona": "parent", "Intent": "filtered_search"},
                {"Query": "best schools for design", "Persona": "advisor", "Intent": "recommendation"},
                {"Query": "best schools for design", "Persona": "parent", "Intent": "recommendation"},
            ]
        )
    duplicate_benchmark_dir = temp_dir / "benchmark_dedup_check"
    run(
        [
            sys.executable,
            str(package_root / "scripts" / "create_validation_benchmark.py"),
            "--source",
            str(duplicate_source_path),
            "--output-dir",
            str(duplicate_benchmark_dir),
            "--benchmark-size",
            "2",
        ],
        cwd=repo_root,
    )
    duplicate_summary = json.loads(
        (duplicate_benchmark_dir / "benchmark_summary.json").read_text(encoding="utf-8")
    )
    assert duplicate_summary["duplicate_same_label_query_rows_dropped"] == 1
    assert duplicate_summary["conflicting_query_groups_excluded"] == 1
    assert duplicate_summary["conflicting_query_rows_excluded"] == 2
    assert duplicate_summary["benchmark_pool_rows"] == 2

    ambiguous_labels = temp_dir / "benchmark_ambiguous_query.csv"
    with labels_path.open("r", encoding="utf-8", newline="") as csv_file:
        label_reader = list(csv.DictReader(csv_file))
        label_fields = label_reader[0].keys()
    ambiguous_rows = [dict(row) for row in label_reader]
    ambiguous_clone = dict(ambiguous_rows[0])
    ambiguous_clone["row_id"] = "step3_9999"
    ambiguous_rows.append(ambiguous_clone)
    with ambiguous_labels.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(label_fields))
        writer.writeheader()
        writer.writerows(ambiguous_rows)
    ambiguous_eval_dir = temp_dir / "evaluation_ambiguous_query"
    ambiguous_failed = run(
        [
            sys.executable,
            str(package_root / "scripts" / "evaluate_classifier.py"),
            "--labels",
            str(ambiguous_labels),
            "--predictions",
            str(query_join_predictions),
            "--output-dir",
            str(ambiguous_eval_dir),
        ],
        cwd=repo_root,
        expect_success=False,
    )
    assert "ambiguous" in (ambiguous_failed.stderr + ambiguous_failed.stdout).lower()

    print(f"Smoke test passed. Outputs available in {temp_dir}")


if __name__ == "__main__":
    main()

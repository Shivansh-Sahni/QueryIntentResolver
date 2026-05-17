from __future__ import annotations

import argparse
import csv
from pathlib import Path


SOURCE_COLUMNS = [
    "Query",
    "Persona",
    "Intent",
    "Complexity",
    "Entities",
    "Route",
    "Notes",
]

OUTPUT_COLUMNS = [
    "row_id",
    "query",
    "persona",
    "seed_intent",
    "seed_complexity",
    "seed_entities",
    "seed_route",
    "seed_notes",
    "gold_route",
    "gold_short_circuit",
    "label_status",
    "reviewer_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a hand-label template from the source query CSV."
    )
    parser.add_argument("--source", required=True, help="Path to the source CSV.")
    parser.add_argument("--output", required=True, help="Path to the output template CSV.")
    return parser.parse_args()


def validate_source_columns(fieldnames: list[str]) -> None:
    missing = [column for column in SOURCE_COLUMNS if column not in fieldnames]
    if missing:
        raise ValueError(f"Source CSV is missing required columns: {', '.join(missing)}")


def build_row(row_id: int, source_row: dict[str, str]) -> dict[str, str]:
    return {
        "row_id": str(row_id),
        "query": source_row["Query"].strip(),
        "persona": source_row["Persona"].strip(),
        "seed_intent": source_row["Intent"].strip(),
        "seed_complexity": source_row["Complexity"].strip(),
        "seed_entities": source_row["Entities"].strip(),
        "seed_route": source_row["Route"].strip(),
        "seed_notes": source_row["Notes"].strip(),
        "gold_route": "",
        "gold_short_circuit": "",
        "label_status": "todo",
        "reviewer_notes": "",
    }


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        if reader.fieldnames is None:
            raise ValueError("Source CSV has no header row.")
        validate_source_columns(reader.fieldnames)
        rows = [build_row(index, row) for index, row in enumerate(reader, start=1)]

    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
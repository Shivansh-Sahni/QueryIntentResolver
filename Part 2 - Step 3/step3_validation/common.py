from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable


CONFIDENCE_BAND_LABELS = ["0.85-1.00", "0.65-0.84", "0.40-0.64", "<0.40"]


def normalized(value: str | None) -> str:
    return (value or "").strip()


def lower_normalized(value: str | None) -> str:
    return normalized(value).lower()


def parse_bool(value: str | None) -> bool | None:
    text = lower_normalized(value)
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_float(value: str | None) -> float | None:
    text = normalized(value)
    if not text:
        return None
    return float(text)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    if lower_index == upper_index:
        return lower_value
    weight = position - lower_index
    return lower_value + (upper_value - lower_value) * weight


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def find_first_key(row: dict[str, str], candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate in row:
            return candidate
    raise KeyError(f"Missing required columns. Looked for one of: {', '.join(candidates)}")


def require_columns(fieldnames: list[str] | None, required_sets: dict[str, list[str]]) -> dict[str, str]:
    if not fieldnames:
        raise ValueError("Input file has no header row.")
    lookup = {name.lower(): name for name in fieldnames}
    resolved: dict[str, str] = {}
    for logical_name, candidates in required_sets.items():
        chosen = ""
        for candidate in candidates:
            actual = lookup.get(candidate.lower())
            if actual:
                chosen = actual
                break
        if not chosen:
            raise ValueError(
                f"Missing column for '{logical_name}'. Expected one of: {', '.join(candidates)}"
            )
        resolved[logical_name] = chosen
    return resolved


def query_sha1(query: str) -> str:
    return hashlib.sha1(query.encode("utf-8")).hexdigest()


def join_key(row: dict[str, str]) -> str:
    row_id = normalized(row.get("row_id"))
    if row_id:
        return f"row_id:{row_id}"
    query = normalized(row.get("query") or row.get("Query"))
    if query:
        return f"query:{query.lower()}"
    raise ValueError("Each row must include either row_id or query.")


def ensure_unique_join_keys(rows: Iterable[dict[str, str]], *, source_name: str) -> None:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[join_key(row)] += 1
    duplicates = [key for key, count in counter.items() if count > 1]
    if duplicates:
        sample = ", ".join(duplicates[:5])
        raise ValueError(f"{source_name} contains duplicate join keys: {sample}")


def entities_text_to_json(raw_value: str | None) -> str:
    text = normalized(raw_value)
    if not text:
        return "[]"
    if text.startswith("["):
        try:
            payload = json.loads(text)
            if isinstance(payload, list):
                return json.dumps([normalized(str(item)) for item in payload if normalized(str(item))])
        except json.JSONDecodeError:
            pass
    parts = [normalized(part) for part in text.split(",")]
    return json.dumps([part for part in parts if part])


def load_route_config(path: Path) -> dict[str, object]:
    payload = load_json(path)
    if "intent_to_route_tier" not in payload:
        raise ValueError("Route config is missing 'intent_to_route_tier'.")
    if "fallback_confidence_below" not in payload:
        raise ValueError("Route config is missing 'fallback_confidence_below'.")
    return payload


def derive_route_tier(
    *,
    intent: str,
    confidence: float | None,
    config: dict[str, object],
    apply_confidence_fallback: bool,
) -> str:
    intent_to_route_tier = config["intent_to_route_tier"]
    if not isinstance(intent_to_route_tier, dict):
        raise ValueError("Route config 'intent_to_route_tier' must be a JSON object.")
    fallback_threshold = float(config["fallback_confidence_below"])

    normalized_intent = normalized(intent)
    route_tier = str(intent_to_route_tier.get(normalized_intent, "fallback"))
    if apply_confidence_fallback and confidence is not None and confidence < fallback_threshold:
        return "fallback"
    return route_tier


def derive_short_circuit(route_tier: str) -> bool:
    return normalized(route_tier) == "short_circuit"


def confidence_band(confidence: float | None) -> str:
    if confidence is None:
        return "<0.40"
    if confidence >= 0.85:
        return "0.85-1.00"
    if confidence >= 0.65:
        return "0.65-0.84"
    if confidence >= 0.40:
        return "0.40-0.64"
    return "<0.40"


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_num(value: float) -> str:
    return f"{value:.2f}"


def html_escape_table(headers: list[str], rows: list[list[str]]) -> str:
    import html

    header_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in headers)
    row_html = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        row_html.append(f"<tr>{cells}</tr>")
    return (
        "<table>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table>"
    )

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

VALID_ROUTES = {"short_circuit", "medium", "complex", "llm_needed"}

SYSTEM_PROMPT = """You are a deterministic query-routing classifier for a college-search product.
Classify the raw query into exactly one route:
- short_circuit: exact entity or directly indexed one-hop fact; no LLM needed
- medium: ordinary structured/semantic search or lightweight factual processing
- complex: comparison, recommendation, ranking, multiple constraints, planning, or multi-step workflow
- llm_needed: subjective, vague, emotional, advisory, or rewrite/interpretation request needing one LLM step

Return JSON only with this schema:
{"route":"short_circuit|medium|complex|llm_needed","confidence":0.0}
Do not answer the query itself."""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in response: {text[:200]!r}")
        return json.loads(match.group(0))


def response_content(payload: dict[str, Any]) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unsupported OpenAI-compatible response: {payload}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an OpenAI-compatible lightweight LLM baseline")
    parser.add_argument("--input", type=Path, required=True, help="Query-only frozen benchmark input")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", default=os.getenv("QIR_LLM_ENDPOINT", ""))
    parser.add_argument("--api-key", default=os.getenv("QIR_LLM_API_KEY", ""))
    parser.add_argument("--auth-header", default=os.getenv("QIR_LLM_AUTH_HEADER", "Authorization"))
    parser.add_argument("--auth-prefix", default=os.getenv("QIR_LLM_AUTH_PREFIX", "Bearer "))
    parser.add_argument("--model", default=os.getenv("QIR_LLM_MODEL", ""))
    parser.add_argument("--input-cost-per-million", type=float, default=0.0)
    parser.add_argument("--output-cost-per-million", type=float, default=0.0)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()
    if not args.endpoint or not args.api_key or not args.model:
        raise SystemExit("Set --endpoint, --api-key, and --model, or the QIR_LLM_* environment variables")

    inputs_frame = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    required = {"benchmark_id", "query_text"}
    if missing := required - set(inputs_frame.columns):
        raise ValueError(f"Benchmark input is missing columns: {sorted(missing)}")
    if {"route", "true_route", "gold_route"} & set(inputs_frame.columns):
        raise ValueError("LLM input must not contain gold labels")

    headers = {"Content-Type": "application/json", args.auth_header: f"{args.auth_prefix}{args.api_key}"}
    rows: list[dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout_seconds) as client:
        for item in inputs_frame.itertuples(index=False):
            payload = {
                "model": args.model,
                "temperature": 0,
                "max_tokens": 40,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": item.query_text},
                ],
            }
            response_json: dict[str, Any] | None = None
            latency_ms = 0.0
            last_error: Exception | None = None
            for attempt in range(args.max_retries):
                try:
                    started = time.perf_counter()
                    response = client.post(args.endpoint, headers=headers, json=payload)
                    latency_ms = (time.perf_counter() - started) * 1000.0
                    response.raise_for_status()
                    response_json = response.json()
                    break
                except Exception as exc:  # provider/network failures are retried, then surfaced
                    last_error = exc
                    if attempt + 1 < args.max_retries:
                        time.sleep(2**attempt)
            if response_json is None:
                raise RuntimeError(f"LLM request failed for {item.benchmark_id}: {last_error}")

            parsed = extract_json(response_content(response_json))
            route = str(parsed.get("route", "")).strip().lower()
            confidence = min(max(float(parsed.get("confidence", 0.0)), 0.0), 1.0)
            if route not in VALID_ROUTES:
                route = "llm_needed"
                confidence = min(confidence, 0.39)

            usage = response_json.get("usage", {}) or {}
            prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
            completion_tokens = int(usage.get("completion_tokens", 0) or 0)
            cost = (
                prompt_tokens * args.input_cost_per_million / 1_000_000
                + completion_tokens * args.output_cost_per_million / 1_000_000
            )
            rows.append(
                {
                    "benchmark_id": item.benchmark_id,
                    "query_text": item.query_text,
                    "predicted_route_raw": route,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "estimated_cost_usd": cost,
                    "model": args.model,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {len(rows)} LLM predictions to {args.output}")


if __name__ == "__main__":
    main()

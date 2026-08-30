from __future__ import annotations

import argparse
import math
import re
import time
from pathlib import Path

import pandas as pd

INTENT_TO_ROUTE = {
    "exact_lookup": "short_circuit",
    "attribute_lookup": "short_circuit",
    "filtered_search": "medium",
    "admissions_process": "medium",
    "career_outcomes": "medium",
    "cost_financial_aid": "medium",
    "b2b_partnership": "medium",
    "profile_management": "medium",
    "multi_constraint": "complex",
    "comparison": "complex",
    "recommendation": "complex",
    "strategy": "complex",
    "analytics_request": "complex",
    "rewrite_needed": "complex",
    "advisory": "llm_needed",
    "emotional_advisory": "llm_needed",
    "reflective_advisory": "llm_needed",
    "campus_life_fit": "llm_needed",
}


def slugify(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_output(response: str) -> tuple[str, str]:
    persona_match = re.search(r"persona\s*[:=]\s*([a-zA-Z0-9_\- ]+)", response, re.IGNORECASE)
    intent_match = re.search(r"intent\s*[:=]\s*([a-zA-Z0-9_\- ]+)", response, re.IGNORECASE)
    persona = slugify(persona_match.group(1).splitlines()[0]) if persona_match else ""
    intent = slugify(intent_match.group(1).splitlines()[0]) if intent_match else ""
    return persona, intent


def geometric_mean(values: list[float]) -> float:
    valid = [max(min(value, 1.0), 1e-12) for value in values]
    return float(math.exp(sum(math.log(value) for value in valid) / len(valid))) if valid else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Anthony's Qwen classifier on the frozen V1 query-only input")
    parser.add_argument("--input", type=Path, required=True, help="qwen_benchmark_input.csv; must not include gold labels")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-name", default="TheCupNoodle/query-intent-classifier")
    parser.add_argument("--max-seq-length", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=50)
    parser.add_argument("--gpu-hourly-cost", type=float, default=0.0)
    args = parser.parse_args()

    try:
        import torch
        from unsloth import FastLanguageModel
    except ImportError as exc:
        raise SystemExit(
            "Qwen benchmark requires CUDA, torch, and unsloth. Run the included notebook on Colab T4/A10."
        ) from exc
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for Anthony's 4-bit Unsloth Qwen model")

    inputs_frame = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    required = {"benchmark_id", "query_text"}
    if missing := required - set(inputs_frame.columns):
        raise ValueError(f"Qwen benchmark input is missing columns: {sorted(missing)}")
    forbidden = {"route", "true_route", "gold_route"} & set(inputs_frame.columns)
    if forbidden:
        raise ValueError(f"Qwen input contains forbidden gold-label columns: {sorted(forbidden)}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    rows: list[dict[str, object]] = []
    for item in inputs_frame.itertuples(index=False):
        prompt = (
            "### Instruction:\nClassify this college-related query.\n"
            f"### Input:\n{item.query_text}\n### Response:"
        )
        encoded = tokenizer(prompt, return_tensors="pt").to("cuda")
        torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=tokenizer.pad_token_id,
            )
        torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - started) * 1000.0

        sequence = generated.sequences[0]
        input_length = encoded["input_ids"].shape[1]
        new_ids = sequence[input_length:]
        response = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        persona, intent = parse_output(response)
        route = INTENT_TO_ROUTE.get(intent, "llm_needed")

        token_probabilities: list[float] = []
        for token_id, scores in zip(new_ids.tolist(), generated.scores):
            token_probabilities.append(float(torch.softmax(scores[0].float(), dim=-1)[token_id].item()))
        confidence = geometric_mean(token_probabilities)
        if intent not in INTENT_TO_ROUTE:
            confidence = min(confidence, 0.39)

        estimated_cost = args.gpu_hourly_cost * (latency_ms / 1000.0) / 3600.0
        rows.append(
            {
                "benchmark_id": item.benchmark_id,
                "query_text": item.query_text,
                "predicted_route_raw": route,
                "confidence": confidence,
                "predicted_intent": intent,
                "predicted_persona": persona,
                "raw_response": response,
                "latency_ms": latency_ms,
                "estimated_cost_usd": estimated_cost,
                "model": "anthony_qwen2_5_3b_lora_intent_to_route",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {len(rows)} Qwen predictions to {args.output}")


if __name__ == "__main__":
    main()

"""Import a submitted review without overwriting the reviewer or the frozen data."""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from .common import ROUTES, dump_json, normalize, sha256

# Closeout adjudications are OUR policy interpretations, not Nimisha's opinions.
# They are deliberately uniform across school/program substitutions.
def adjudicate(text: str, confidence: str) -> tuple[str | None, str]:
    q = normalize(text)
    if confidence in {"context-dependent", "context_dependent"}:
        return None, "Retain outside supervised training: reviewer identified missing context."
    if q.endswith("housing guarantee"):
        return "short_circuit", "Named-school housing-policy field lookup; short circuit only when the deployed index actually supports that field."
    if q.endswith("admissions profile average sat and gpa"):
        return "medium", "Retrieve two admissions-profile attributes for one school; no comparison, personalization or multi-step planning is requested."
    if q.startswith("four year cost of ") and q.endswith(" including housing"):
        return "complex", "Multi-year combined cost estimate requires explicit assumptions and composition; apply the same tier to every school."
    if q.startswith("create reach target safety list for "):
        return "complex", "Personalized multi-constraint list construction and reach/target/safety classification require a multi-step workflow."
    if q.endswith(" financial aid") or q.endswith(" scholarships"):
        return "medium", "General school-specific financial-aid information search rather than one named indexed numeric field."
    if q == "colleges near tech hubs":
        return "medium", "Geographical college-discovery search; hub definitions must be supplied by the retrieval system."
    if q.startswith("how to advise students who want to work abroad"):
        return "llm_needed", "Open-ended advising request, not a single factual lookup."
    if q == "schools with strong honors programs":
        return "llm_needed", "Qualitative program-strength interpretation; no explicit multi-step personalized plan is requested."
    if q == "what is demonstrated interest and does it matter":
        return "medium", "Admissions-process explanation retrieved from guidance; no personal recommendation is requested."
    return None, "No predeclared closeout adjudication applies; retain for later context rather than guess."

def integrate_review(received: Path, queue: Path, training: Path, benchmark: Path, out: Path) -> tuple[pd.DataFrame, dict]:
    r = pd.read_csv(received, dtype=str, keep_default_na=False)
    q = pd.read_csv(queue, dtype=str, keep_default_na=False)
    t = pd.read_csv(training, dtype=str, keep_default_na=False)
    b = pd.read_csv(benchmark, dtype=str, keep_default_na=False)
    required = {"query_id", "query_text", "review_route", "review_notes", "review_confidence"}
    if required - set(r):
        raise ValueError(f"Review missing columns: {sorted(required - set(r))}")
    if r.query_id.duplicated().any() or r.query_text.map(normalize).duplicated().any():
        raise ValueError("Duplicate review identities")
    if any(r[c].str.strip().eq("").any() for c in required):
        raise ValueError("Blank required review field")
    if set(r.review_route) - set(ROUTES):
        raise ValueError("Unknown reviewed route")
    allowed = {"high", "medium", "context-dependent", "context_dependent"}
    if set(r.review_confidence) - allowed:
        raise ValueError("Unknown review confidence")
    if set(r.query_id) != set(q.query_id):
        raise ValueError("Submitted review IDs do not exactly match the quarantine queue")
    lookup = q.set_index("query_id")
    audit = []
    rows = []
    for item in r.to_dict("records"):
        old = lookup.loc[item["query_id"]]
        if normalize(item["query_text"]) != normalize(old["query_text"]):
            raise ValueError(f"Query mismatch for {item['query_id']}")
        route, reason = adjudicate(item["query_text"], item["review_confidence"])
        disposition = "deferred_context" if route is None else ("accepted_unchanged" if route == item["review_route"] else "policy_adjudicated")
        audit.append({**item, "original_reviewer": "Nimisha Sambhaktula",
                      "final_route": route or "", "disposition": disposition,
                      "closeout_rationale": reason, "closeout_label_source": "assistant_policy_review_2026-09-29"})
        if route is not None:
            row = {c: "" for c in t.columns}
            row.update(query_id=item["query_id"], query_text=item["query_text"],
                       query_norm=normalize(item["query_text"]), route=route)
            for col in ("source_files", "source_rows", "canonical_intent", "persona_hint"):
                if col in t:
                    row[col] = str(old.get(col, ""))
            row["label_source"] = "closeout_policy_review_of_submitted_annotation"
            rows.append(row)
    t["label_source"] = "legacy_cleaned_corpus"
    merged = pd.concat([t, pd.DataFrame(rows)], ignore_index=True).fillna("")
    if merged.query_id.duplicated().any() or merged.query_text.map(normalize).duplicated().any():
        raise ValueError("Reviewed IDs or normalized queries collide with the original training data")
    overlap = set(merged.query_text.map(normalize)) & set(b.query_text.map(normalize))
    if overlap:
        raise ValueError("Frozen benchmark leakage in reviewed training data")
    out.mkdir(parents=True, exist_ok=True)
    a = pd.DataFrame(audit)
    a.to_csv(out / "review_audit.csv", index=False)
    a[a.disposition == "deferred_context"].to_csv(out / "deferred_context.csv", index=False)
    merged.to_csv(out / "training_reviewed.csv", index=False)
    summary = {
        "submitted_rows": len(r), "queue_rows": len(q), "exact_id_match": True,
        "all_required_fields_present": True, "duplicate_ids": 0,
        "original_review_sha256": sha256(received),
        "accepted_unchanged": int((a.disposition == "accepted_unchanged").sum()),
        "policy_adjudicated": int((a.disposition == "policy_adjudicated").sum()),
        "deferred_context": int((a.disposition == "deferred_context").sum()),
        "training_rows_before": len(t), "training_rows_after": len(merged),
        "benchmark_exact_overlap": 0,
        "warning": "Structural completeness is not semantic agreement. Original labels/notes are preserved; policy corrections are separately attributed, not presented as the reviewer's decisions. Context-dependent rows stay quarantined."
    }
    dump_json(out / "review_summary.json", summary)
    return merged, summary

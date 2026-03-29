from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from resolver_utils import count_school_mentions, normalize_query_text


CANONICAL_PERSONAS = {
    "advisor",
    "college_b2b",
    "college_student",
    "counselor_teacher",
    "high_school_student",
    "parent",
}

CANONICAL_INTENTS = {
    "admissions_process",
    "attribute_lookup",
    "b2b_partnership",
    "campus_life_fit",
    "career_outcomes",
    "comparison",
    "cost_financial_aid",
    "direct_lookup",
    "filtered_search",
    "multi_constraint",
    "recommendation",
    "rewrite_needed",
}

CANONICAL_PRIMARY_ROUTES = {
    "b2b",
    "llm",
    "retrieval",
    "shortcut",
}

PERSONA_MAP = {
    "advisor": "advisor",
    "community_college_advisor": "advisor",
    "district_advisor": "advisor",
    "independent_counselor": "advisor",
    "nonprofit_advisor": "advisor",
    "college_student": "college_student",
    "community_college_student": "college_student",
    "transfer_student": "college_student",
    "graduate_applicant": "college_student",
    "international_student": "college_student",
    "career_changer": "college_student",
    "high_school_student": "high_school_student",
    "highschool_student": "high_school_student",
    "counselor": "counselor_teacher",
    "counselor_teacher": "counselor_teacher",
    "teacher": "counselor_teacher",
    "school_counselor": "counselor_teacher",
    "rural_teacher": "counselor_teacher",
    "urban_teacher": "counselor_teacher",
    "parent": "parent",
    "college_b2b": "college_b2b",
    "colleges_b2b": "college_b2b",
    "college": "college_b2b",
    "college_admissions_officer": "college_b2b",
}

INTENT_MAP = {
    "admissions_process": "admissions_process",
    "attribute_lookup": "attribute_lookup",
    "b2b_partnership": "b2b_partnership",
    "campus_life_fit": "campus_life_fit",
    "career_outcomes": "career_outcomes",
    "comparison": "comparison",
    "cost_financial_aid": "cost_financial_aid",
    "exact_lookup": "direct_lookup",
    "direct_lookup": "direct_lookup",
    "filtered_search": "filtered_search",
    "filter_search": "filtered_search",
    "multi_constraint": "multi_constraint",
    "recommendation": "recommendation",
    "rewrite_needed": "rewrite_needed",
}

FIT_QUERY_RE = re.compile(
    r"\b(?:normal people|introverts?|friendly|belonging|campus life|sports culture|"
    r"fun campus life|low stress|stressful|vibe|fit me|fits me|college fits me)\b"
)
RECOMMEND_QUERY_RE = re.compile(
    r"\b(?:what colleges should i apply to|help me pick a school|what school is good for me|"
    r"should i go to a big school|schools like |recommend )\b"
)
ADMISSIONS_QUERY_RE = re.compile(
    r"\b(?:apply|application|admission|admissions|deadline|deadlines|essay|essays|sat|gpa)\b"
)
COST_QUERY_RE = re.compile(r"\b(?:cost|tuition|financial aid|scholarship|fafsa|loans?|afford|price)\b")
CAREER_QUERY_RE = re.compile(r"\b(?:job|career|outcomes|placement|internship)\b")
REWRITE_QUERY_RE = re.compile(r"\b(?:cheaper|less stressful|not so expensive|without the suffering)\b")
B2B_QUERY_RE = re.compile(
    r"\b(?:demo|api|partner|pricing|platform|profile data|institutional|crm|admissions team)\b"
)
BROAD_SEARCH_RE = re.compile(r"\b(?:schools|colleges|universities)\b")

ROUTE_TO_INTENT_MAP = {
    "b2b_portal": "b2b_partnership",
    "comparison_engine": "comparison",
    "compare_majors": "comparison",
    "financial_aid_advising": "cost_financial_aid",
    "financial_aid_info": "cost_financial_aid",
    "sales_pipeline": "b2b_partnership",
    "simple_entity_info": "direct_lookup",
    "typesense_only": "direct_lookup",
}

B2B_SOURCE_INTENTS = {
    "profile_management",
    "pricing",
    "support_request",
    "technical",
}

RAW_ROUTE_TO_PRIMARY_ROUTE = {
    "academic_advising": "retrieval",
    "academic_life_info": "retrieval",
    "academic_planning_advising": "retrieval",
    "academic_policy_info": "retrieval",
    "academic_program_info": "retrieval",
    "admissions_info": "retrieval",
    "agentic": "retrieval",
    "analytics": "retrieval",
    "analytics_filter": "retrieval",
    "analytics_route": "retrieval",
    "application_advising": "retrieval",
    "b2b_portal": "b2b",
    "campus_services_info": "retrieval",
    "career_advising": "retrieval",
    "career_services_info": "retrieval",
    "college_prep_info": "retrieval",
    "college_search": "retrieval",
    "college_selection_advising": "retrieval",
    "compare_majors": "retrieval",
    "comparison_engine": "retrieval",
    "counselor_professional_dev": "retrieval",
    "counselor_resources": "retrieval",
    "counselor_student_advising": "retrieval",
    "counselor_tools": "retrieval",
    "course_selection_advising": "retrieval",
    "credit_transfer": "retrieval",
    "degree_planning": "retrieval",
    "filter_search": "retrieval",
    "filtered_search": "retrieval",
    "financial_aid_advising": "retrieval",
    "financial_aid_info": "retrieval",
    "grad_school_advising": "retrieval",
    "housing_advising": "retrieval",
    "llm": "llm",
    "llm_advisory": "llm",
    "llm_recommendation": "llm",
    "llm_strategy": "llm",
    "major_change_advising": "retrieval",
    "major_selection_advising": "retrieval",
    "metric_lookup": "retrieval",
    "opportunity_search": "retrieval",
    "parent_college_advising": "retrieval",
    "pathway_search": "retrieval",
    "platform_pricing": "b2b",
    "platform_support": "b2b",
    "policy_lookup": "retrieval",
    "sales_pipeline": "b2b",
    "search": "retrieval",
    "short_circuit": "shortcut",
    "simple_entity_info": "shortcut",
    "student_finance_advising": "retrieval",
    "student_life_advising": "retrieval",
    "student_wellbeing_advising": "retrieval",
    "study_abroad_advising": "retrieval",
    "test_prep_advising": "retrieval",
    "transfer_advising": "retrieval",
    "typesense_only": "shortcut",
    "undergraduate_research_advising": "retrieval",
}

INTENT_TO_PRIMARY_ROUTE = {
    "direct_lookup": "shortcut",
    "attribute_lookup": "shortcut",
    "filtered_search": "retrieval",
    "multi_constraint": "retrieval",
    "comparison": "retrieval",
    "recommendation": "retrieval",
    "admissions_process": "retrieval",
    "cost_financial_aid": "retrieval",
    "career_outcomes": "retrieval",
    "campus_life_fit": "llm",
    "rewrite_needed": "llm",
    "b2b_partnership": "b2b",
}


def slugify_label(value: object) -> str:
    lowered = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def standardize_persona(raw_persona: object) -> tuple[str | None, str]:
    persona_key = slugify_label(raw_persona)
    persona = PERSONA_MAP.get(persona_key)
    if persona is None:
        return None, "persona:unmapped"
    return persona, f"persona:{persona_key}->{persona}"


def standardize_intent(raw_intent: object, raw_route: object, query_text: str) -> tuple[str | None, str]:
    intent_key = slugify_label(raw_intent)
    route_key = slugify_label(raw_route)
    query_lower = str(query_text or "").strip().lower()

    if intent_key in INTENT_MAP:
        standardized = INTENT_MAP[intent_key]
        return standardized, f"intent:{intent_key}->{standardized}"

    if intent_key in B2B_SOURCE_INTENTS or route_key in {"platform_pricing", "platform_support"}:
        return "b2b_partnership", f"intent:{intent_key or route_key}->b2b_partnership"

    if route_key in ROUTE_TO_INTENT_MAP:
        standardized = ROUTE_TO_INTENT_MAP[route_key]
        return standardized, f"route:{route_key}->{standardized}"

    if intent_key in {"advisory", "emotional_advisory"}:
        if RECOMMEND_QUERY_RE.search(query_lower):
            return "recommendation", f"intent:{intent_key}->recommendation"
        if FIT_QUERY_RE.search(query_lower):
            return "campus_life_fit", f"intent:{intent_key}->campus_life_fit"
        if ADMISSIONS_QUERY_RE.search(query_lower) and route_key == "admissions_info":
            return "admissions_process", f"intent:{intent_key}+route:{route_key}->admissions_process"
        if route_key in {"financial_aid_advising", "financial_aid_info"}:
            return "cost_financial_aid", f"intent:{intent_key}+route:{route_key}->cost_financial_aid"

    return None, "intent:unmapped"


def clean_query_text(query_text: object) -> str:
    return re.sub(r"\s+", " ", str(query_text or "").strip())


def derive_primary_route(
    *,
    query_text: str,
    intent: str,
    raw_route: object,
    raw_complexity: object,
) -> tuple[str | None, str]:
    route_key = slugify_label(raw_route)
    complexity_key = slugify_label(raw_complexity)
    normalized = normalize_query_text(query_text)

    if route_key in RAW_ROUTE_TO_PRIMARY_ROUTE:
        return RAW_ROUTE_TO_PRIMARY_ROUTE[route_key], f"primary_route:route:{route_key}"

    if complexity_key == "short_circuit":
        return "shortcut", "primary_route:complexity:short_circuit"
    if complexity_key == "llm_needed":
        return "llm", "primary_route:complexity:llm_needed"

    if B2B_QUERY_RE.search(normalized):
        return "b2b", "primary_route:query:b2b_pattern"

    primary_route = INTENT_TO_PRIMARY_ROUTE.get(intent)
    if primary_route is None:
        return None, "primary_route:unmapped"
    return primary_route, f"primary_route:intent:{intent}->{primary_route}"


def refine_standardized_intent(query_text: str, persona: str, intent: str) -> tuple[str | None, str]:
    normalized = normalize_query_text(query_text)
    broad_search = bool(BROAD_SEARCH_RE.search(normalized))
    school_mentions = count_school_mentions(normalized)
    word_count = len(normalized.split())

    if intent == "direct_lookup":
        if broad_search or word_count > 4 or ADMISSIONS_QUERY_RE.search(normalized) or COST_QUERY_RE.search(normalized):
            return None, "intent:direct_lookup_rejected_not_entity_like"
        return intent, "intent:validated_direct_lookup"

    if intent == "attribute_lookup":
        if broad_search and school_mentions == 0:
            return "filtered_search", "intent:attribute_lookup_broad_search->filtered_search"
        return intent, "intent:validated_attribute_lookup"

    if intent == "comparison":
        if school_mentions == 0:
            return None, "intent:comparison_rejected_non_school"
        return intent, "intent:validated_comparison"

    if intent == "recommendation":
        if RECOMMEND_QUERY_RE.search(normalized):
            return intent, "intent:validated_recommendation"
        if broad_search:
            return "filtered_search", "intent:recommendation_broad_search->filtered_search"
        return intent, "intent:validated_recommendation"

    return intent, f"intent:validated_{intent}"


def load_and_standardize_sources(paths: Iterable[Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    accepted_rows: list[dict[str, object]] = []
    rejected_rows: list[dict[str, object]] = []
    source_summaries: list[dict[str, object]] = []

    for path in paths:
        df = pd.read_csv(path)
        accepted_before = len(accepted_rows)
        rejected_before = len(rejected_rows)

        for row in df.itertuples(index=False):
            query_text = clean_query_text(getattr(row, "Query", ""))
            raw_persona = getattr(row, "Persona", "")
            raw_intent = getattr(row, "Intent", "")
            raw_route = getattr(row, "Route", "")
            raw_complexity = getattr(row, "Complexity", "")
            raw_entities = getattr(row, "Entities", "")
            raw_notes = getattr(row, "Notes", "")

            if not query_text or query_text.lower() == "query":
                rejected_rows.append(
                    {
                        "query_text": query_text,
                        "raw_persona": raw_persona,
                        "raw_intent": raw_intent,
                        "raw_route": raw_route,
                        "source_file": path.name,
                        "rejection_reason": "query:blank_or_header",
                    }
                )
                continue

            persona, persona_note = standardize_persona(raw_persona)
            intent, intent_note = standardize_intent(raw_intent, raw_route, query_text)

            if persona is None or intent is None:
                rejected_rows.append(
                    {
                        "query_text": query_text,
                        "raw_persona": raw_persona,
                        "raw_intent": raw_intent,
                        "raw_route": raw_route,
                        "source_file": path.name,
                        "rejection_reason": persona_note if persona is None else intent_note,
                    }
                )
                continue

            refined_intent, refinement_note = refine_standardized_intent(query_text, persona, intent)
            if refined_intent is None:
                rejected_rows.append(
                    {
                        "query_text": query_text,
                        "raw_persona": raw_persona,
                        "raw_intent": raw_intent,
                        "raw_route": raw_route,
                        "source_file": path.name,
                        "rejection_reason": refinement_note,
                    }
                )
                continue

            primary_route, primary_route_note = derive_primary_route(
                query_text=query_text,
                intent=refined_intent,
                raw_route=raw_route,
                raw_complexity=raw_complexity,
            )
            if primary_route is None:
                rejected_rows.append(
                    {
                        "query_text": query_text,
                        "raw_persona": raw_persona,
                        "raw_intent": raw_intent,
                        "raw_route": raw_route,
                        "source_file": path.name,
                        "rejection_reason": primary_route_note,
                    }
                )
                continue

            accepted_rows.append(
                {
                    "query_text": query_text,
                    "persona": persona,
                    "intent_label": refined_intent,
                    "primary_route": primary_route,
                    "complexity": clean_query_text(raw_complexity),
                    "entities": clean_query_text(raw_entities),
                    "route": clean_query_text(raw_route),
                    "notes": clean_query_text(raw_notes),
                    "source_file": path.name,
                    "raw_persona": raw_persona,
                    "raw_intent": raw_intent,
                    "raw_route": raw_route,
                    "standardization_notes": ",".join([persona_note, intent_note, refinement_note, primary_route_note]),
                }
            )

        source_summaries.append(
            {
                "source_file": path.name,
                "raw_rows": int(len(df)),
                "accepted_rows_before_dedup": int(len(accepted_rows) - accepted_before),
                "rejected_rows": int(len(rejected_rows) - rejected_before),
            }
        )

    accepted = pd.DataFrame(accepted_rows)
    rejected = pd.DataFrame(rejected_rows)

    accepted_before_dedup = len(accepted)
    if not accepted.empty:
        accepted = accepted.drop_duplicates(subset=["query_text", "persona", "intent_label"]).reset_index(drop=True)

    summary = {
        "accepted_rows_before_dedup": int(accepted_before_dedup),
        "accepted_rows_after_dedup": int(len(accepted)),
        "duplicate_rows_removed": int(accepted_before_dedup - len(accepted)),
        "rejected_rows": int(len(rejected)),
        "canonical_personas": sorted(CANONICAL_PERSONAS),
        "canonical_intents": sorted(CANONICAL_INTENTS),
        "canonical_primary_routes": sorted(CANONICAL_PRIMARY_ROUTES),
        "source_summary": source_summaries,
    }
    return accepted, rejected, summary


def default_training_source_paths(base_dir: Path) -> list[Path]:
    return [
        base_dir / "Data" / "Data - Anika.csv",
        base_dir / "Data" / "Data - Edward.csv",
        base_dir / "Data" / "Data - Nimisha.csv",
        base_dir / "Data" / "Data - Ridhi.csv",
        base_dir / "Data" / "Data - Shivansh.csv",
        base_dir / "Data" / "Data Anthony.csv",
    ]


def write_standardized_dataset_artifacts(
    *,
    base_dir: Path,
    out_dir: Path,
    paths: Iterable[Path] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    source_paths = list(paths or default_training_source_paths(base_dir))
    accepted, rejected, summary = load_and_standardize_sources(source_paths)

    out_dir.mkdir(parents=True, exist_ok=True)
    accepted.to_csv(out_dir / "standardized_training_dataset.csv", index=False)
    rejected.to_csv(out_dir / "rejected_training_rows.csv", index=False)
    (out_dir / "training_standardization_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return accepted, rejected, summary

from __future__ import annotations

import re
from typing import Any

import pandas as pd


ROUTE_MAP = {
    "direct_lookup": "typesense_only",
    "attribute_lookup": "typesense_plus_metadata",
    "filtered_search": "semantic_or_faceted_search",
    "multi_constraint": "foundry_multi_agent",
    "comparison": "compare_pipeline",
    "recommendation": "recommendation_workflow",
    "admissions_process": "faq_or_guidance",
    "cost_financial_aid": "finance_guidance",
    "campus_life_fit": "llm_advisory",
    "career_outcomes": "outcomes_pipeline",
    "rewrite_needed": "rewrite_then_route",
    "b2b_partnership": "b2b_workflow",
}

TIER_MAP = {
    "direct_lookup": "easy",
    "attribute_lookup": "easy",
    "filtered_search": "medium",
    "admissions_process": "medium",
    "cost_financial_aid": "medium",
    "career_outcomes": "medium",
    "b2b_partnership": "medium",
    "multi_constraint": "complex",
    "comparison": "complex",
    "recommendation": "complex",
    "campus_life_fit": "complex",
    "rewrite_needed": "complex",
}

KNOWN_SCHOOLS = [
    "arizona state",
    "boston university",
    "brown",
    "carnegie mellon",
    "columbia",
    "cornell",
    "duke",
    "georgia tech",
    "harvard",
    "maryland",
    "mit",
    "northwestern",
    "nyu",
    "penn state",
    "princeton",
    "purdue",
    "rice university",
    "stanford",
    "ucla",
    "uc berkeley",
    "university of florida",
    "university of maryland",
    "university of michigan",
    "university of washington",
    "university of wisconsin",
    "usc",
    "ut austin",
    "vanderbilt",
    "virginia tech",
]

SCHOOL_PATTERN = r"(?:%s)" % "|".join(re.escape(name) for name in sorted(KNOWN_SCHOOLS, key=len, reverse=True))
SCHOOL_RE = re.compile(rf"\b{SCHOOL_PATTERN}\b")

B2B_RE = re.compile(
    r"\b(?:api|demo|partner|partners|pricing|platform|enterprise|districts|"
    r"update our school profile|admissions team|admissions office|join the platform)\b"
)
COMPARE_RE = re.compile(r"\bvs\b|\bcompare\b")
REWRITE_RE = re.compile(r"\bbut cheaper\b|\bbut less\b|\bwithout the\b|\bvibe but\b")
CAMPUS_RE = re.compile(r"\bvibe\b|\bchill\b|\bnormal people\b|\bintroverts\b|\bsports culture\b|\bculture\b")
CAREER_RE = re.compile(r"\bjob\b|\bcareer\b|\boutcomes\b|\bplacement\b|\binternship\b")
ADMISSIONS_RE = re.compile(r"\bneed sat\b|\bsat\b|\bgpa\b|\bessay\b|\bdeadline\b|\bdeadlines\b|\badmissions\b|\bapplication\b")
COST_RE = re.compile(r"\bfinancial aid\b|\bscholarships?\b|\bafford\b|\bcost\b|\btuition\b|\bfull ride\b")
ATTRIBUTE_RE = re.compile(r"\bhousing(?: policy| guarantee)?\b|\bacceptance rate\b|\boverview\b")
RECOMMEND_RE = re.compile(r"\brecommend\b|\bschools like\b|\bbest options\b")
PROGRAM_RE = re.compile(
    r"\b(?:architecture|biology|business|computer science|cs|economics|engineering|film|"
    r"mechanical engineering|neuroscience|nursing|pre-law|pre med|pre-med|psychology)\b"
)
LOCATION_RE = re.compile(
    r"\b(?:california|chicago|east coast|florida|midwest|texas|warm states|"
    r"near the beach|beach|warm)\b"
)


def normalize_query_text(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def count_school_mentions(query_text: str) -> int:
    return len(SCHOOL_RE.findall(query_text))


def is_school_only_query(query_text: str) -> bool:
    return bool(re.fullmatch(rf"{SCHOOL_PATTERN}(?: overview)?", query_text))


def compute_constraint_score(query_text: str) -> int:
    return (
        len(re.findall(r"\bwith\b", query_text))
        + len(re.findall(r"\bunder\b|\bless than\b", query_text))
        + len(re.findall(r"\bnear\b|\bin\b.+\b(?:states|california|texas|midwest|chicago|east coast|warm|beach)\b", query_text))
        + len(re.findall(r"\bsmall\b|\bstrong\b|\bgood\b|\bscholarships?\b", query_text))
    )


def extract_entity_types(query_text: str) -> str:
    normalized = normalize_query_text(query_text)
    entity_types: list[str] = []
    school_mentions = count_school_mentions(normalized)

    if school_mentions:
        entity_types.append("school")
    if school_mentions > 1 or COMPARE_RE.search(normalized):
        entity_types.append("comparison_target")
    if PROGRAM_RE.search(normalized):
        entity_types.append("major_or_program")
    if LOCATION_RE.search(normalized):
        entity_types.append("location")
    if COST_RE.search(normalized):
        entity_types.append("cost_constraint")
    if ADMISSIONS_RE.search(normalized) or ATTRIBUTE_RE.search(normalized):
        entity_types.append("admissions_or_attribute_signal")
    if CAMPUS_RE.search(normalized):
        entity_types.append("fit_or_culture_cue")
    if CAREER_RE.search(normalized):
        entity_types.append("career_outcome_cue")
    if B2B_RE.search(normalized):
        entity_types.append("b2b_request_type")
    if REWRITE_RE.search(normalized):
        entity_types.append("rewrite_cue")

    return ",".join(entity_types)


def canonicalize_persona(query_text: str, persona: str) -> tuple[str, list[str]]:
    normalized = normalize_query_text(query_text)
    updated_persona = persona
    flags: list[str] = []

    def override(new_persona: str, flag: str) -> None:
        nonlocal updated_persona
        if updated_persona != new_persona:
            updated_persona = new_persona
            flags.append(flag)

    if B2B_RE.search(normalized):
        override("college_b2b", "persona:b2b_pattern")
    if "research opportunities for undergrads" in normalized:
        override("college_student", "persona:undergrad_research_pattern")
    if "can i transfer credits into" in normalized:
        override("college_student", "persona:transfer_credit_pattern")
    if "best options for a student switching into" in normalized:
        override("advisor", "persona:advisor_switching_pattern")
    if "create reach target safety list for" in normalized:
        override("advisor", "persona:advisor_list_pattern")
    if "best fit colleges for students interested in" in normalized:
        override("counselor_teacher", "persona:counselor_best_fit_pattern")
    if "schools with strong first gen support" in normalized:
        override("counselor_teacher", "persona:counselor_first_gen_pattern")
    if "schools with strong support for first generation students" in normalized:
        override("counselor_teacher", "persona:counselor_first_gen_pattern")
    if "admissions profile average sat and gpa" in normalized:
        override("counselor_teacher", "persona:counselor_admissions_profile_pattern")
    if "safe for students" in normalized:
        override("parent", "persona:parent_safety_pattern")
    if "four year cost of" in normalized:
        override("parent", "persona:parent_cost_pattern")
    if "housing guarantee" in normalized:
        override("parent", "persona:parent_housing_pattern")
    if is_school_only_query(normalized):
        override("high_school_student", "persona:school_only_pattern")

    return updated_persona, flags


def canonicalize_persona_and_intent(query_text: str, persona: str, intent: str) -> tuple[str, str, list[str]]:
    normalized = normalize_query_text(query_text)
    updated_persona, persona_flags = canonicalize_persona(query_text, persona)
    updated_intent = "direct_lookup" if intent == "exact_lookup" else intent
    flags: list[str] = persona_flags.copy()

    school_mentions = count_school_mentions(normalized)
    constraint_score = compute_constraint_score(normalized)
    broad_search_language = bool(re.search(r"\bschools\b|\bcolleges\b|\buniversities\b", normalized))
    is_b2b = bool(B2B_RE.search(normalized))
    is_compare = bool(COMPARE_RE.search(normalized))
    needs_rewrite = bool(REWRITE_RE.search(normalized))
    is_campus = bool(CAMPUS_RE.search(normalized))
    is_career = bool(CAREER_RE.search(normalized))
    is_admissions = bool(ADMISSIONS_RE.search(normalized))
    is_recommendation = bool(RECOMMEND_RE.search(normalized))
    is_cost = bool(COST_RE.search(normalized))
    is_attribute = bool(ATTRIBUTE_RE.search(normalized))

    if is_b2b:
        if updated_intent != "b2b_partnership":
            flags.append("intent:b2b_override")
        return "college_b2b", "b2b_partnership", flags

    if "research opportunities for undergrads" in normalized:
        if updated_intent != "attribute_lookup":
            flags.append("intent:undergrad_research_pattern")
        updated_intent = "attribute_lookup"
    elif "can i transfer credits into" in normalized:
        if updated_intent != "admissions_process":
            flags.append("intent:transfer_credit_pattern")
        updated_intent = "admissions_process"
    elif "four year cost of" in normalized:
        if updated_intent != "cost_financial_aid":
            flags.append("intent:four_year_cost_pattern")
        updated_intent = "cost_financial_aid"
    elif "housing guarantee" in normalized:
        if updated_intent != "attribute_lookup":
            flags.append("intent:housing_guarantee_pattern")
        updated_intent = "attribute_lookup"
    elif "admissions profile average sat and gpa" in normalized:
        if updated_intent != "admissions_process":
            flags.append("intent:admissions_profile_pattern")
        updated_intent = "admissions_process"
    elif "safe for students" in normalized:
        if updated_intent != "attribute_lookup":
            flags.append("intent:safety_attribute_pattern")
        updated_intent = "attribute_lookup"
    elif "best options for a student switching into" in normalized:
        if updated_intent != "recommendation":
            flags.append("intent:advisor_switching_pattern")
        updated_intent = "recommendation"
    elif "best fit colleges for students interested in" in normalized:
        if updated_intent != "recommendation":
            flags.append("intent:best_fit_pattern")
        updated_intent = "recommendation"
    elif "schools with strong first gen support" in normalized or "schools with strong support for first generation students" in normalized:
        if updated_intent != "filtered_search":
            flags.append("intent:first_gen_support_pattern")
        updated_intent = "filtered_search"
    elif "create reach target safety list for" in normalized:
        if updated_intent != "multi_constraint":
            flags.append("intent:advisor_list_pattern")
        updated_intent = "multi_constraint"
    if is_school_only_query(normalized):
        if updated_intent != "direct_lookup":
            flags.append("intent:school_only_lookup")
        updated_intent = "direct_lookup"
    elif is_compare:
        if updated_intent != "comparison":
            flags.append("intent:comparison_pattern")
        updated_intent = "comparison"
    elif needs_rewrite:
        if updated_intent != "rewrite_needed":
            flags.append("intent:rewrite_pattern")
        updated_intent = "rewrite_needed"
    elif is_campus:
        if updated_intent != "campus_life_fit":
            flags.append("intent:campus_fit_pattern")
        updated_intent = "campus_life_fit"
    elif is_career:
        if updated_intent != "career_outcomes":
            flags.append("intent:career_pattern")
        updated_intent = "career_outcomes"
    elif is_recommendation:
        if updated_intent != "recommendation":
            flags.append("intent:recommendation_pattern")
        updated_intent = "recommendation"
    elif is_admissions and school_mentions <= 1:
        if updated_intent != "admissions_process":
            flags.append("intent:admissions_pattern")
        updated_intent = "admissions_process"
    elif is_cost and school_mentions == 1:
        if updated_intent != "cost_financial_aid":
            flags.append("intent:cost_pattern")
        updated_intent = "cost_financial_aid"
    elif is_attribute and school_mentions == 1 and not is_cost:
        if updated_intent != "attribute_lookup":
            flags.append("intent:attribute_pattern")
        updated_intent = "attribute_lookup"
    elif broad_search_language and constraint_score >= 3:
        if updated_intent != "multi_constraint":
            flags.append("intent:multi_constraint_pattern")
        updated_intent = "multi_constraint"
    elif (
        broad_search_language
        and not is_compare
        and not needs_rewrite
        and not is_recommendation
        and not is_career
        and not is_campus
        and not is_admissions
        and not is_cost
    ):
        if updated_intent != "filtered_search":
            flags.append("intent:filtered_search_pattern")
        updated_intent = "filtered_search"

    return updated_persona, updated_intent, flags


def normalize_labeled_dataframe(
    df: pd.DataFrame,
    *,
    query_col: str,
    persona_col: str,
    intent_col: str,
    route_col: str,
    tier_col: str,
) -> pd.DataFrame:
    normalized = df.copy()

    personas: list[str] = []
    intents: list[str] = []
    flags_list: list[str] = []
    entity_types: list[str] = []

    for row in normalized.itertuples(index=False):
        query_text = getattr(row, query_col)
        persona = getattr(row, persona_col)
        intent = getattr(row, intent_col)
        updated_persona, updated_intent, flags = canonicalize_persona_and_intent(query_text, persona, intent)
        personas.append(updated_persona)
        intents.append(updated_intent)
        flags_list.append(",".join(flags))
        entity_types.append(extract_entity_types(query_text))

    normalized[persona_col] = personas
    normalized[intent_col] = intents
    normalized[route_col] = normalized[intent_col].map(ROUTE_MAP)
    normalized[tier_col] = normalized[intent_col].map(TIER_MAP)
    normalized["entity_types"] = entity_types
    normalized["normalization_flags"] = flags_list
    return normalized


def apply_strict_rule_layer(df: pd.DataFrame, *, query_col: str = "query_text") -> pd.DataFrame:
    ruled = df.copy()
    query_series = ruled[query_col].fillna("").map(normalize_query_text)
    word_count = query_series.str.split().str.len()
    school_mentions = query_series.map(count_school_mentions)

    ruled["rule_persona"] = ""
    ruled["rule_intent"] = ""

    b2b_mask = query_series.str.contains(B2B_RE)
    ruled.loc[b2b_mask, "rule_persona"] = "college_b2b"
    ruled.loc[b2b_mask, "rule_intent"] = "b2b_partnership"

    school_lookup_mask = query_series.map(is_school_only_query) & ~b2b_mask
    ruled.loc[school_lookup_mask, "rule_intent"] = "direct_lookup"

    attribute_lookup_mask = (
        query_series.str.contains(ATTRIBUTE_RE)
        & school_mentions.eq(1)
        & word_count.le(5)
        & ~query_series.str.contains(COMPARE_RE)
        & ~b2b_mask
    )
    ruled.loc[attribute_lookup_mask, "rule_intent"] = "attribute_lookup"
    return ruled


def confidence_from_pipeline(model: Any, texts: pd.Series) -> list[float]:
    probabilities = model.predict_proba(texts)
    return probabilities.max(axis=1).tolist()

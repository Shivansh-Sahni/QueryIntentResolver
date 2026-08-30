from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Route = Literal["short_circuit", "medium", "complex", "llm_needed"]


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(min_length=1, max_length=4000)
    persona: str | None = None
    page: str | None = None
    filters: dict[str, Any] | None = None
    context: list[dict[str, Any]] | dict[str, Any] | None = None
    session: dict[str, Any] | None = None
    include_optional_fields: bool = False


class ResolveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, Any] | None = None
    intent: str | None = None
    raw_route: Route | None = None
    policy_reason: str | None = None
    latency_ms: float | None = None
    context_used: bool | None = None

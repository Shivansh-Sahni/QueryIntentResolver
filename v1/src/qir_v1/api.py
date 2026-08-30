from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from .resolver import QueryIntentResolver
from .schemas import ResolveRequest, ResolveResponse


@lru_cache(maxsize=1)
def get_resolver() -> QueryIntentResolver:
    model_path = os.getenv("QIR_MODEL_PATH", "v1/artifacts/release/model.joblib")
    policy_path = os.getenv("QIR_POLICY_PATH", "v1/config/route_policy.json")
    return QueryIntentResolver(model_path=model_path, policy_path=policy_path)


app = FastAPI(
    title="Query Intent Resolver V1",
    version="1.0.0",
    description="Classifies raw college-product queries into one of four handling routes.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        get_resolver()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Resolver model is not ready") from exc
    return {"status": "ready", "version": "1.0.0"}


@app.post("/v1/resolve", response_model=ResolveResponse, response_model_exclude_none=True)
def resolve(request: ResolveRequest) -> dict:
    try:
        return get_resolver().resolve(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Resolver inference failed") from exc

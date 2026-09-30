"""App factory usable with a trusted local bundle or a test resolver."""
from __future__ import annotations
import hmac, os
from contextlib import asynccontextmanager
from typing import Any, Literal
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from .runtime import Resolver, validate_query

class ResolveRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    query_text: StrictStr = Field(min_length=1,max_length=2048)
    persona: Any=None
    page: Any=None
    filters: Any=None
    context: Any=None
    session: Any=None
    @field_validator("query_text")
    @classmethod
    def valid_text(cls,v):
        return validate_query(v)

class ResolveResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    route: Literal["short_circuit","medium","complex","llm_needed"]
    confidence: float=Field(ge=0,le=1)

class BatchRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    queries: list[ResolveRequest]=Field(min_length=1,max_length=100)


def create_app(resolver: Resolver | None=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.resolver=resolver or Resolver()
        yield
    app=FastAPI(title="Query Intent Resolver",version="1.1.0",lifespan=lifespan,
                description="Query-only routing component. No actual downstream execution. Production authorization is separate from service availability.")
    if resolver is not None: app.state.resolver=resolver
    def authorization(x_api_key: str | None=Header(default=None)):
        key=os.environ.get("QIR_API_KEY")
        if key and (x_api_key is None or not hmac.compare_digest(x_api_key,key)):
            raise HTTPException(401,"Invalid API key")
    def get_resolver():
        r=getattr(app.state,"resolver",None)
        if r is None: raise HTTPException(503,"Resolver not initialized")
        return r
    @app.get("/health",operation_id="service_health")
    def health(): return {"status":"up"}
    @app.get("/ready",operation_id="service_ready",dependencies=[Depends(authorization)])
    def ready():
        r=get_resolver()
        return {"ready":True,"version":"1.1.0","production_authorized":False,
                "quality_status":r.info.get("quality_status","unassessed")}
    @app.post("/v1/resolve",response_model=ResolveResponse,operation_id="resolve_query",dependencies=[Depends(authorization)])
    def resolve(request:ResolveRequest):
        return get_resolver().resolve(**request.model_dump())
    @app.post("/v1/resolve/batch",response_model=list[ResolveResponse],operation_id="resolve_batch",dependencies=[Depends(authorization)])
    def resolve_batch(request:BatchRequest):
        r=get_resolver()
        return [r.resolve(**item.model_dump()) for item in request.queries]
    return app

app=create_app()

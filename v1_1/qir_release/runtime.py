"""Small, offline query-only runtime. No downstream calls or raw-query logging."""
from __future__ import annotations
import os
from pathlib import Path
import joblib
from .common import ROUTES, load_json, sha256
from .modeling import RoutingPolicy, probabilities, input_guard

MAX_QUERY_CHARS = 2048

def validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise ValueError("query_text must be a string")
    if not query.strip():
        raise ValueError("query_text must not be blank")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query_text exceeds {MAX_QUERY_CHARS} characters")
    if any(ord(c) < 32 and c not in "\t\n\r" for c in query):
        raise ValueError("query_text contains unsupported control characters")
    return query

class Resolver:
    def __init__(self, bundle: Path | str | None = None, *, model=None, policy=None):
        self.info = {"version":"1.1.0", "scope":"query_only", "production_authorized":False}
        if model is not None:
            self.model=model
            self.policy=policy or RoutingPolicy()
            return
        folder=Path(bundle or os.environ.get("QIR_BUNDLE",Path(__file__).resolve().parents[1]/"artifacts"/"release"))
        manifest=load_json(folder/"manifest.json")
        if manifest["model_sha256"] != sha256(folder/"model.joblib"):
            raise ValueError("Model integrity check failed; refusing deserialization")
        if manifest["policy_sha256"] != sha256(folder/"policy.json"):
            raise ValueError("Policy integrity check failed")
        # Only trusted repository-built artifacts are supported. A SHA check is
        # integrity checking, not authentication of an untrusted pickle.
        self.model=joblib.load(folder/"model.joblib")
        self.policy=RoutingPolicy(**load_json(folder/"policy.json"))
        self.info.update(manifest)

    def debug(self, query_text: str, **optional_context) -> dict:
        query=validate_query(query_text)
        if input_guard(query):
            return {"route":"llm_needed","confidence":0.0,"decision_source":"unsupported_or_guarded_input","context_used":False}
        p=probabilities(self.model,[query])[0]
        result=self.policy.decide(query,p)
        result["context_used"]=False
        return result

    def resolve(self, query_text: str, **optional_context) -> dict:
        d=self.debug(query_text,**optional_context)
        return {"route":d["route"],"confidence":round(float(d["confidence"]),6)}

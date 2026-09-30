"""Explicit local binding seam; never invent URLs or invoke a service implicitly."""
from __future__ import annotations
import hashlib,hmac
from dataclasses import dataclass
from typing import Callable
from .common import ROUTES

@dataclass
class RouterBindings:
    handlers: dict[str,Callable]
    def __post_init__(self):
        if set(self.handlers)!=set(ROUTES) or not all(callable(v) for v in self.handlers.values()):
            raise ValueError("All four routes must have explicit callable handlers")
    def dispatch(self,decision:dict,query_text:str):
        if decision.get("route") not in self.handlers:
            raise ValueError("Unknown route; refusing arbitrary dispatch")
        return self.handlers[decision["route"]](query_text)

def private_telemetry(query:str,decision:dict,key:bytes) -> dict:
    if len(key)<32: raise ValueError("Telemetry requires a separate key of at least 32 bytes")
    return {"query_hmac":hmac.new(key,query.encode(),hashlib.sha256).hexdigest(),
            "route":decision["route"],"confidence":float(decision["confidence"]),"version":"1.1.0"}

def deployment_preflight(config:dict,quality_passed:bool) -> dict:
    missing=[]
    if not quality_passed: missing.append("model_quality_gate")
    if config.get("mode")!="production": missing.append("explicit_production_mode")
    if not config.get("approved_by_product_owner"): missing.append("product_owner_approval")
    if not config.get("real_traffic_validated"): missing.append("independent_real_traffic_validation")
    if set(config.get("route_bindings",{}))!=set(ROUTES) or not all(config.get("route_bindings",{}).values()):
        missing.append("four_concrete_route_bindings")
    return {"production_allowed":not missing,"missing":missing}

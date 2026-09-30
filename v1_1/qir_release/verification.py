from __future__ import annotations
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from fastapi.testclient import TestClient
from .api import create_app
from .common import dump_json
from .integration import deployment_preflight


def verify_runtime(resolver, suite, out):
    out.mkdir(parents=True,exist_ok=True)
    client=TestClient(create_app(resolver))
    checks=[]
    def record(name, passed):
        checks.append({"check":name,"passed":bool(passed)})
    with client:
        record("health",client.get("/health").status_code==200)
        record("ready",client.get("/ready").json().get("ready") is True)
        for query in suite.query_text.tolist():
            r=client.post("/v1/resolve",json={"query_text":query})
            expected=resolver.resolve(query)
            record("request_contract_and_parity",r.status_code==200 and r.json()==expected and set(r.json())=={"route","confidence"})
        for value in ("", "   ", "a"*2049, 123, None, ["MIT"], "MIT\x00"):
            record("invalid_input_rejected",client.post("/v1/resolve",json={"query_text":value}).status_code==422)
        base=client.post("/v1/resolve",json={"query_text":"MIT"}).json()
        extra={"query_text":"MIT","persona":"parent","page":"chat","filters":{"cost":1000},"context":[{"role":"user","content":"different prior query"}],"session":{"id":"test"}}
        record("optional_context_decoupled",client.post("/v1/resolve",json=extra).json()==base)
        record("unexpected_field_rejected",client.post("/v1/resolve",json={"query_text":"MIT","unknown":True}).status_code==422)
        record("batch_contract",client.post("/v1/resolve/batch",json={"queries":[{"query_text":"MIT"},{"query_text":"colleges in California"}]}).status_code==200)
        record("batch_bound",client.post("/v1/resolve/batch",json={"queries":[{"query_text":"MIT"}]*101}).status_code==422)
        spec=client.get("/openapi.json").json()
        dump_json(out/"openapi.json",spec)
    queries=(suite.query_text.tolist()*9)[:1000]
    t=time.perf_counter()
    serial=[resolver.resolve(q) for q in queries]
    serial_seconds=time.perf_counter()-t
    t=time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        parallel=list(pool.map(resolver.resolve,queries))
    concurrent_seconds=time.perf_counter()-t
    record("threaded_determinism",serial==parallel)
    report={"checks":len(checks),"passed":sum(c["passed"] for c in checks),"failed":[c for c in checks if not c["passed"]],
            "load":{"queries":len(queries),"sequential_seconds":serial_seconds,"sequential_queries_per_second":len(queries)/serial_seconds,
                    "four_threads_seconds":concurrent_seconds,"four_threads_queries_per_second":len(queries)/concurrent_seconds,
                    "scope":"in-process CPU requests, no hosting/network/downstream calls"},
            "production_preflight":deployment_preflight({},False)}
    dump_json(out/"verification.json",report)
    if report["failed"]: raise AssertionError("Runtime verification failed")
    return report

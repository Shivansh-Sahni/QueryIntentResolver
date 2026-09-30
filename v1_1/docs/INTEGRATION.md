# Integration contract and deployment boundary

## Component, not an autonomous answer engine

The resolver determines a routing label; it does not fetch a school fact, produce counseling advice, authorize a profile mutation or initiate a financial action. Every downstream handler must enforce its own authorization, data freshness, privacy and content safety.

The four labels are operational categories, not an ordinal certainty scale. `complex` can require a multi-step workflow. `llm_needed` can mean clarification or unstructured interpretation and is also the uncertainty fallback; it is not automatically an adequate single-call answer path for any unknown request.

## Explicit bindings

`qir_release.integration.RouterBindings` requires all four callables. Missing bindings raise an error. A local demonstration can use functions that return their own names; that is a mock demonstration, not MascotGO integration. Do not fill configuration with guessed internal URLs.

```python
from qir_release.runtime import Resolver
from qir_release.integration import RouterBindings
resolver = Resolver()
# Supply four authorized application functions after product-owner approval.
result = resolver.resolve("UCLA vs USC for engineering")
```

A short-circuit decision is conditional on the entity being unambiguous and the requested fact being present and current in the index. The downstream lookup must decline or escalate if either condition fails. A route label is not evidence that the underlying data exists.

## Request and response

`POST /v1/resolve` with a nonblank `query_text` string of at most 2,048 characters. Optional persona, page, filters, context and session do not affect V1.1 prediction. Successful response contains exactly route and confidence; request errors return HTTP 422 rather than a fabricated route.

`POST /v1/resolve/batch` accepts `{"queries":[...ResolveRequest...]}`, 1–100 entries. The batch is validated before execution.

`GET /health` means the process is up. `GET /ready` means the trusted model loaded; production_authorized remains false. This service is deliberately not an implicit deployment approval mechanism.

## Foundry

The executed app's OpenAPI 3.1 schema is exported to `artifacts/verification/openapi.json`. Operation IDs use letters and underscores. For an approved Foundry tool registration, add the deployed HTTPS server URL and correct authentication configuration to a copy of the schema. Do not confuse the Foundry project endpoint with the resolver endpoint. No tool registration or cloud deployment has been performed by this package.

Reference: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/openapi

## Security and privacy

The local default binds to loopback. An externally exposed deployment requires an approved TLS gateway, authentication, rate limits, input/body limits, retention policy and access monitoring. QIR_API_KEY is supported through X-API-Key; never commit the key. CORS is not opened permissively. The application does not log raw requests. Optional telemetry uses keyed HMAC with a separate secret; plain unsalted hashes of common queries are not treated as anonymization.

The guard is a limited heuristic. It does not comprehensively detect injection, abuse or all unsupported language. The resolver executes no tools based on the query and cannot override downstream safety policy.

## Rollback

Retain both `v1/artifacts/release/` and `v1_1/artifacts/release/` with their pinned code and dependencies. Never load an older sklearn pickle with an arbitrary unpinned environment. Route traffic through the previously approved backend only; model choice alone does not grant production approval.

## External decisions still required

Peter/MascotGO: invocation surfaces, route-to-handler mapping, supported index fields and entity disambiguation, context availability, hosting pattern, privacy-safe real-query data and acceptance tolerances. These are outside the completed standalone engineering package.

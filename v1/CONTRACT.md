# Query Intent Resolver V1 Technical Contract

## Objective

Given raw user query text, determine the minimum handling complexity and routing tier needed to answer it correctly.

## Required input

```json
{
  "query_text": "affordable engineering schools in California with good job placement"
}
```

## Required output

```json
{
  "route": "complex",
  "confidence": 0.91
}
```

`route` must be exactly one of:

- `short_circuit`
- `medium`
- `complex`
- `llm_needed`

`confidence` must be a number from 0 to 1.

## Optional future inputs

The interface accepts optional fields for forward compatibility:

- persona
- current page
- selected filters
- prior conversation context
- session or account context

These fields are deliberately ignored by the V1 classifier. Raw query text is the only model input. This prevents MascotGO integration details from blocking the first usable implementation.

## Optional future outputs

- `entities`
- `intent`

They are reserved but excluded from the default V1 response.

## Safety behavior

- Globally low-confidence classifications escalate to `llm_needed`.
- A low-confidence `short_circuit` classification escalates to `medium`.
- The API does not silently return an unknown route.

## Integration boundary

The stable integration surface is:

- Python: `QueryIntentResolver.resolve(query_text)`
- HTTP: `POST /v1/resolve`

The exact MascotGO or Microsoft Foundry binding remains configurable until Peter confirms where routing output enters the application architecture.

---
name: kelvin-docs
description: "Look up Kelvin platform concepts, SDK, API, or infrastructure documentation. Auto-activates when the user asks about Kelvin platform topics like assets, datastreams, apps, NATS, bridges, workloads, SDK usage, or API endpoints."
user-invocable: false
---

# Kelvin Platform Knowledge Base

The structured knowledge base for the Kelvin platform lives in the `kelvin-ai-docs` submodule.

## Locating the Docs

```bash
ls kelvin-ai-docs/docs-ai/ 2>/dev/null || echo "Docs not found — run: git submodule update --init"
```

## Query Strategy

| Question Type | Where to Look |
|---------------|---------------|
| Concepts (what is an asset, datastream, app) | `kelvin-ai-docs/docs-ai/concepts/` |
| REST API endpoints (create asset, list workloads) | `kelvin-ai-docs/docs-ai/api/endpoints/` |
| API schemas (data structures) | `kelvin-ai-docs/docs-ai/api/schemas/` |
| Python SDK (KelvinApp, stream_filter, entry points) | `kelvin-ai-docs/docs-ai/sdk/` |
| How-to guides (deploy app, configure bridge) | `kelvin-ai-docs/docs-ai/how-to/development/` |
| Infrastructure (k3s, NATS, edge clusters) | `kelvin-ai-docs/docs-ai/infra/` |

## Search Priority

1. **Concepts first** — for "what is X?" questions
2. **How-to guides** — for "how do I X?" questions
3. **API endpoints** — for REST API questions
4. **SDK classes** — for Python code questions
5. **Infrastructure** — for cluster/deployment questions

## Reading the Docs

Documentation files are JSON with the schema:
```json
{
  "id": "...",
  "title": "...",
  "type": "...",
  "category": "...",
  "content": "full content text",
  "summary": "brief summary",
  "code_examples": [...],
  "related": [...],
  "tags": [...]
}
```

- Use `summary` for quick answers, `content` for detailed ones.
- For API endpoints: check `metadata.method`, `metadata.path`, `metadata.parameters`, `metadata.request_body`.

## Important: API Conventions

When the docs reference REST API endpoints:
- Base path: `/api/v4`
- List endpoints use `/list` suffix
- Response data in `data` key, NOT `items`
- Use the REST API tools (`tools/assets.py`, etc.) for live queries

## Rules

- Read `kelvin-ai-docs/docs-ai/agents.md` first if you need guidance on how to search the docs.
- If the submodule is not initialized, instruct the user to run `git submodule update --init`.
- Prefer `summary` for quick answers, full `content` when the user needs detail.

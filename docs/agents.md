# AI Agent Guide for Kelvin Documentation

This guide explains how AI CLI tools and agents can effectively use the Kelvin documentation for RAG, context injection, and answering user questions.

## Documentation Structure

```
docs-ai/
├── concepts/           # Core platform concepts (start here)
├── api/endpoints/      # REST API reference
├── api/schemas/        # Data type definitions
├── sdk/                # Python SDK classes and methods
├── how-to/             # Step-by-step guides
├── infra/              # Infrastructure docs (K3s, services, troubleshooting)
├── tools/              # Support operations tools (Jira, Keycloak, SSH, cluster-debug, etc.)
├── index.jsonl         # All documents (for vector DB ingestion)
└── manifest.json       # Metadata and statistics
```

## Document Schema

Every document follows this structure:

```json
{
  "id": "concepts/core/asset",           // Unique identifier
  "title": "Asset",                       // Human-readable title
  "type": "concept|api_endpoint|schema|sdk_class|how_to",
  "category": "core|data|applications|api|sdk|development|operations",
  "content": "Full markdown content...",
  "summary": "1-2 sentence description",
  "source": "Original source file path",
  "code_examples": [{"language": "python", "code": "..."}],
  "related": ["concepts/data/data-stream", "api/endpoints/asset/..."],
  "tags": ["asset", "data", "platform"],
  "metadata": { /* type-specific metadata */ }
}
```

## Query Strategies

Note: The examples below use `jq`. Install it or replace with a small Python script if it is not available.

### 1. Concept Questions
**User asks:** "What is an asset in Kelvin?"

**Strategy:** Search `concepts/` directory first
```bash
# Find by keyword in filename
docs-ai/concepts/core/asset.json

# Or search index.jsonl for type=concept
jq 'select(.type == "concept" and (.title | test("asset"; "i")))' index.jsonl
```

**Key fields to return:** `summary`, `content`, `related`

### 2. API Questions
**User asks:** "How do I create an asset via API?"

**Strategy:** Search `api/endpoints/` by operation
```bash
# Find create operations for assets
docs-ai/api/endpoints/asset/createAssetBulk.json

# Or search by tag
jq 'select(.type == "api_endpoint" and (.tags | contains(["asset"])))' index.jsonl
```

**Key fields to return:**
- `metadata.path` - The endpoint URL
- `metadata.method` - HTTP method
- `metadata.parameters` - Request parameters
- `metadata.request_body.schema` - Request body structure
- `code_examples` - curl and Python examples

### 3. SDK Questions
**User asks:** "How do I use KelvinApp to publish data?"

**Strategy:** Search `sdk/app/` for class documentation
```bash
# Find the main app class
docs-ai/sdk/app/kelvinapp.json

# Search for specific methods
jq 'select(.type == "sdk_class" and (.metadata.methods | contains(["publish"])))' index.jsonl
```

**Key fields to return:**
- `content` - Class documentation with methods
- `metadata.methods` - List of available methods
- `code_examples` - Usage examples

### 4. How-To Questions
**User asks:** "How do I deploy a SmartApp?"

**Strategy:** Search `how-to/` by keywords
```bash
# Search development guides
docs-ai/how-to/development/deploy*.json

# Or search by tags
jq 'select(.type == "how_to" and (.tags | contains(["deploy"])))' index.jsonl
```

**Key fields to return:**
- `content` - Step-by-step instructions
- `metadata.steps` - Extracted numbered steps
- `code_examples` - Command examples

### 5. Support Tool Questions
**User asks:** "How do I create a Keycloak user?" or "Search Jira for open TST tickets"

**Strategy:** Search `tools/` directory
```bash
# Find by tool name
docs-ai/tools/user-creation.json
docs-ai/tools/jira-search.json

# Or search by tags
jq 'select(.category == "tools" and (.tags | contains(["keycloak"])))' index.jsonl
```

**Key fields to return:**
- `content` - CLI usage, parameters, dependencies
- `code_examples` - Ready-to-run commands
- `metadata.env_vars` - Required environment variables
- `metadata.forbidden_scripts` - Scripts that must NOT be run by AI (interactive, will hang)

### Available Tools

| Doc | Tool | Purpose |
|-----|------|---------|
| `tools/jira-read.json` | jira_read.py | Read ticket details |
| `tools/jira-write.json` | jira_write.py | Create/comment/assign/transition tickets |
| `tools/jira-search.json` | jira_search.py | Search with JQL |
| `tools/user-creation.json` | user-creation app | Keycloak user provisioning |
| `tools/ssh-key-manager.json` | ssh-key-manager | SSH access management |
| `tools/cluster-debug.json` | cluster_debug.py | Remote kubectl/shell on edge clusters |
| `tools/jira-triage-agent.json` | jira-triage-agent | AI Slack bot for ticket triage |
| `tools/grafana-alerts.json` | grafana_alerts.py | Manage Grafana alert rules |
| `tools/slack-fetch.json` | fetch_conversation.py | Export Slack conversations |
| `tools/auth-check.json` | auth tools | Verify credentials |
| `tools/platform-communications.json` | whats-new emails | Release announcements |
| `tools/check-assetdata.json` | asset checker | Asset availability health check |
| `tools/asset-activity-checker.json` | activity checker | Historian data freshness |
| `tools/control-changes-validator.json` | control validator | Detect automation drift |
| `tools/environment-config.json` | .ai/config.json | Environment name→URL registry |

## Recommended Search Priority

For general questions, search in this order:

1. **Concepts first** - Understand the domain
2. **How-to guides** - Practical instructions
3. **Support tools** - CLI tools and operational scripts
4. **API endpoints** - Technical implementation
5. **SDK classes** - Code-level details
6. **Schemas** - Data structure reference
7. **Infrastructure** - K3s, services, troubleshooting

## Context Window Optimization

### For Limited Context (4K-8K tokens)
Return only:
- `summary` field
- Relevant `code_examples`
- First 500 chars of `content`

### For Medium Context (16K-32K tokens)
Return:
- Full `content`
- All `code_examples`
- `related` document summaries

### For Large Context (100K+ tokens)
Can include:
- Multiple related documents
- Full API schemas
- Complete how-to sequences

## Vector Database Ingestion

### Using index.jsonl for RAG

```python
import json

# Load all documents
with open('docs-ai/index.jsonl') as f:
    documents = [json.loads(line) for line in f]

# Create embeddings from summary + title + tags
for doc in documents:
    text_to_embed = f"{doc['title']}: {doc['summary']} Tags: {', '.join(doc['tags'])}"
    # Generate embedding and store with doc ID
```

### Chunking Strategy

For large documents, chunk by:
1. **Concepts:** Keep whole (usually < 2K tokens)
2. **API endpoints:** Keep whole with schema
3. **SDK classes:** Split by method if > 4K tokens
4. **How-to:** Split by H2 sections

## Common Query Patterns

### Pattern 1: Definition Query
```
User: "What is a data stream?"
→ Search: concepts/ for "data-stream"
→ Return: summary + first content section
```

### Pattern 2: Implementation Query
```
User: "How do I read timeseries data?"
→ Search: how-to/ for "timeseries" + "download"
→ Search: api/endpoints/timeseries/
→ Search: sdk/ for timeseries methods
→ Return: Combined how-to steps + code examples
```

### Pattern 3: Troubleshooting Query
```
User: "Why is my SmartApp not receiving data?"
→ Search: concepts/ for "data-stream", "connection"
→ Search: how-to/ for "monitor", "logs", "troubleshoot"
→ Return: Relevant diagnostic steps
```

### Pattern 4: Code Generation Query
```
User: "Write code to publish a recommendation"
→ Search: sdk/app/ for "publish", "recommendation"
→ Search: concepts/ for "recommendation"
→ Return: SDK class docs + code_examples + concept context
```

## Metadata Quick Reference

### API Endpoint Metadata
```json
{
  "path": "/assets/bulk/create",
  "method": "POST",
  "operation_id": "createAssetBulk",
  "tag": "Asset",
  "permission": "kelvin.permission.asset.create",
  "parameters": [...],
  "request_body": { "schema": {...} },
  "responses": { "201": {...}, "400": {...} }
}
```

### SDK Class Metadata
```json
{
  "package": "app",
  "module": "application.client",
  "item_type": "class",
  "methods": ["connect", "publish", "filter", ...]
}
```

### How-To Metadata
```json
{
  "subcategory": "deployment",
  "steps": [
    {"step": 1, "instruction": "Create the app manifest"},
    {"step": 2, "instruction": "Upload to registry"}
  ],
  "step_count": 5
}
```

## Document Type Reference

| Type | Count | Use For |
|------|-------|---------|
| `concept` | 18 | Understanding platform concepts |
| `api_endpoint` | 251 | API implementation details |
| `schema` | 188 | Data structure definitions |
| `sdk_class` | 1115 | Python SDK usage |
| `how_to` | 198 | Step-by-step procedures |
| `ops_guide` | 53 | Infrastructure, troubleshooting, and support tools |

## Category Reference

| Category | Description | Example Questions |
|----------|-------------|-------------------|
| `core` | Platform fundamentals | "What is an asset?" |
| `data` | Data streams, properties | "How does data flow?" |
| `applications` | SmartApps, Docker apps | "What app types exist?" |
| `api` | REST API reference | "How do I call the API?" |
| `sdk` | Python SDK | "How do I use KelvinApp?" |
| `development` | Developer guides | "How do I create an app?" |
| `operations` | Admin/ops guides | "How do I manage clusters?" |
| `infrastructure` | K3s, services, troubleshooting | "Why is Keycloak returning 401?" |
| `tools` | Support operations tools | "How do I create a Jira ticket?" |

## Example: Full Query Resolution

**User Question:** "How do I create a SmartApp that monitors temperature and sends alerts?"

**Agent Resolution Steps:**

1. **Understand concepts:**
   - Read `concepts/applications/smart-app.json` - What is a SmartApp
   - Read `concepts/data/data-stream.json` - How data flows
   - Read `concepts/core/recommendation.json` - How to send alerts

2. **Find implementation guide:**
   - Read `how-to/development/develop_create.json` - Create app steps
   - Read `how-to/development/develop_consume_timeseries-data-messages.json` - Read data
   - Read `how-to/development/develop_produce_recommendation-messages.json` - Send alerts

3. **Get code reference:**
   - Read `sdk/app/kelvinapp.json` - Main SDK class
   - Read `sdk/app/messagebuilder.json` - How to build messages

4. **Synthesize response:**
   - Combine concept explanations
   - Provide step-by-step from how-to
   - Include code examples from SDK docs

## Tips for Effective Usage

1. **Start broad, then narrow** - Begin with concepts, drill into specifics
2. **Use `related` field** - Follow document relationships
3. **Check `tags`** - Quick filtering across document types
4. **Include code examples** - Users usually want working code
5. **Link to sources** - Reference `source` field for verification
6. **Respect document types** - Concepts explain "what", how-to explains "how"

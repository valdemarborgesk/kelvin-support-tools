# Kelvin Support Tools — AI Instructions

## Purpose

This toolkit equips AI agents with everything needed to troubleshoot Kelvin SmartApps and platform issues. It provides diagnostic access to the platform API, remote cluster debugging, ClickHouse data queries (via Grafana proxy), and platform documentation.

## Target Audience

The user is a **technical person** who builds or operates Kelvin apps. They understand concepts like clusters, pods, data streams, and APIs — but they want the AI to do the investigative legwork. This means:

- **Be thorough but efficient.** The user can follow technical explanations, but they want answers, not a lecture. Lead with findings, then explain the reasoning.
- **Investigate before asking.** Don't ask "what cluster is it on?" — look it up. Don't ask "what data streams does it use?" — list them. Only ask when you genuinely need human input (which environment, what's the expected behavior, should I restart it).
- **Follow the diagnostic methodology.** Don't jump to conclusions. Check logs, check data, check infrastructure — in that order.
- **If the SDK doesn't work, use the API.** Some SDK CLI commands have bugs or require complex config files. The REST API is often simpler. Check `kelvin-ai-docs/docs-ai/api/endpoints/` for alternatives.
- **Use ClickHouse for deep data analysis.** The REST API timeseries endpoints are good for quick checks, but ClickHouse (via Grafana proxy) is the power tool — aggregations, gap detection, cross-asset comparisons.

## Diagnostic Methodology

When something is wrong, follow this order:

```
1. UNDERSTAND → What's the symptom? What's expected vs actual?
2. CHECK STATUS → Is the workload running? What state is it in?
3. CHECK LOGS → What errors are in the workload logs?
4. FOLLOW THE DATA → Is data flowing in? Is the app processing it? Is output coming out?
5. CHECK INFRASTRUCTURE → Cluster/node health, resource limits, network
6. DEEP DIVE → ClickHouse queries, raw kubectl, pod describe
```

Don't skip steps. A workload in CrashLoopBackOff is visible at step 2 — no need to query ClickHouse. An app that's running but not producing data needs steps 3-4.

## Quick Setup

```bash
bash scripts/setup.sh
source venv/bin/activate
```

For first-time auth (macOS native dialogs, no Terminal needed):
```bash
venv/bin/python scripts/auth-dialog.py https://<env-url>
```

For subsequent logins:
```bash
kelvin auth login https://<env-url>
```

## Tool Priority

1. **SDK CLI** (`kelvin ...`) — workload status, logs, start/stop, auth
2. **REST API tools** (`venv/bin/python tools/...`) — assets, datastreams, timeseries, clusters
3. **ClickHouse via Grafana** (`venv/bin/python tools/grafana_client.py`) — deep data analysis, gap detection, aggregations
4. **Cluster debug** (`venv/bin/python tools/cluster_debug.py`) — remote kubectl, pod logs, exec on edge clusters

## Authentication

**First-time login** (macOS native dialogs):
```bash
venv/bin/python scripts/auth-dialog.py https://<env-url>
```

**Subsequent logins** (keyring picks up stored credentials):
```bash
source venv/bin/activate && kelvin auth login https://<env-url>
```

**Check current auth:**
```bash
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

**Credential flow:**
- `auth-dialog.py` → stores tokens in macOS keyring via Kelvin SDK
- `kelvin auth login` → reads keyring automatically
- `api_client.py` / `cluster_debug.py` → gets JWT from `kelvin auth token`
- `grafana_client.py` → uses same Keycloak credentials via OAuth flow (no separate Grafana creds)

## SDK CLI Reference

| Task | Command |
|------|---------|
| First login (dialog) | `venv/bin/python scripts/auth-dialog.py https://<url>` |
| Login (keyring) | `kelvin auth login https://<url>` |
| Check auth | `kelvin auth token 2>/dev/null \| grep '^ey' \| tail -1` |
| List workloads | `kelvin workload list` |
| Show workload | `kelvin workload show <name>` |
| View logs | `kelvin workload logs <name> --tail-lines 100` |
| Start workload | `kelvin workload start <name>` |
| Stop workload | `kelvin workload stop <name>` |
| Search workloads | `kelvin workload search --app-name <name>` |
| List platform apps | `kelvin apps list` |
| Show app details | `kelvin apps show <name>` |
| List secrets | `kelvin secret list` |

## REST API Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `tools/assets.py` | Asset + asset type CRUD | `venv/bin/python tools/assets.py --env <env> list --search pump` |
| `tools/datastreams.py` | Data stream inspection | `venv/bin/python tools/datastreams.py --env <env> list --asset pump-01` |
| `tools/timeseries.py` | Quick timeseries queries | `venv/bin/python tools/timeseries.py --env <env> latest --asset pump-01 --datastream temp` |
| `tools/clusters.py` | Cluster + node health | `venv/bin/python tools/clusters.py --env <env> list` |
| `tools/api_spec.py` | Fetch + check API spec | `venv/bin/python tools/api_spec.py --env <env> fetch` |

All tools accept `--env <name>` (from `config.json`) or `--url <full-url>`.

### API Spec Verification

After first login to any environment, fetch its OpenAPI spec:

```bash
venv/bin/python tools/api_spec.py --env <env> fetch
```

Before calling any API endpoint you're unsure about, verify it exists:

```bash
venv/bin/python tools/api_spec.py --env <env> check /assets/list GET
venv/bin/python tools/api_spec.py --env <env> search workload
venv/bin/python tools/api_spec.py --env <env> version
```

The spec is cached locally in `.cache/api-specs/`. Re-fetch after platform upgrades.

## ClickHouse via Grafana

Query ClickHouse through the Grafana datasource proxy. No separate ClickHouse credentials needed.

```bash
venv/bin/python tools/grafana_client.py --env <env> query "SELECT count() FROM kelvin.assets"
venv/bin/python tools/grafana_client.py --env <env> tables
venv/bin/python tools/grafana_client.py --env <env> schema assets
venv/bin/python tools/grafana_client.py --env <env> alerts list
```

### ClickHouse Schema (database: `kelvin`)

**Timeseries tables** (`timeseries_ad_float`, `timeseries_ad_bool`, `timeseries_ad_string`):

| Column | Type | Description |
|--------|------|-------------|
| timestamp | DateTime64(6) | Data point timestamp |
| asset_name | String | Asset that produced the data |
| datastream_name | String | Data stream name |
| value | Float64/Bool/String | The data value |
| resource | String | Resource identifier |
| inserted_at | DateTime64(6) | When inserted into ClickHouse |

**No `cluster_name` column** — filter by `asset_name` instead.

**Platform tables:** `app_workloads`, `assets`, `data_streams`, `clusters` — mirror the REST API data.

### Common Diagnostic Queries

```sql
-- Data flow check: what's flowing in the last hour?
SELECT asset_name, datastream_name, count() as pts, max(timestamp) as latest
FROM kelvin.timeseries_ad_float
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY asset_name, datastream_name
ORDER BY pts DESC LIMIT 20

-- Data flow for a specific asset: last data per stream
SELECT datastream_name, max(timestamp) as last_ts, count() as pts_24h
FROM kelvin.timeseries_ad_float
WHERE asset_name = '{asset}' AND timestamp > now() - INTERVAL 24 HOUR
GROUP BY datastream_name

-- Data gaps: hourly point counts (look for zeros)
SELECT toStartOfHour(timestamp) as hour, count() as points
FROM kelvin.timeseries_ad_float
WHERE asset_name = '{asset}' AND datastream_name = '{ds}'
  AND timestamp > now() - INTERVAL 7 DAY
GROUP BY hour ORDER BY hour

-- Compare data rates across assets (spot the outlier)
SELECT asset_name, count() as pts_1h
FROM kelvin.timeseries_ad_float
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY asset_name ORDER BY pts_1h ASC

-- Workload status from ClickHouse
SELECT name, app_name, app_version, cluster_name, status, updated
FROM kelvin.app_workloads
WHERE name LIKE '%{search}%' ORDER BY updated DESC
```

## Cluster Debug

Remote kubectl and shell access to edge clusters via the Kelvin API (proxied through NATS/edge-updater). No SSH required.

```bash
# List pods on a cluster
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl get pods -A

# View pod logs
venv/bin/python tools/cluster_debug.py --env <env> <cluster> logs <pod-name> -n kelvin --tail 100

# Run arbitrary command
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "df -h"

# Deploy debug pod (for host-level access)
venv/bin/python tools/cluster_debug.py --env <env> <cluster> deploy-debug

# Host-level command via debug pod
venv/bin/python tools/cluster_debug.py --env <env> <cluster> host "top -bn1 | head -20"
```

## Environment Configuration

Environments are in `config.json`. Use `--env <name>` with any tool.

## Platform Documentation

| Topic | Path |
|-------|------|
| Concepts (assets, data streams, apps) | `kelvin-ai-docs/docs-ai/concepts/` |
| REST API endpoints | `kelvin-ai-docs/docs-ai/api/endpoints/` |
| API schemas | `kelvin-ai-docs/docs-ai/api/schemas/` |
| Python SDK | `kelvin-ai-docs/docs-ai/sdk/` |
| Development how-to guides | `kelvin-ai-docs/docs-ai/how-to/development/` |
| Infrastructure (k3s, NATS, clusters) | `kelvin-ai-docs/docs-ai/infra/` |

See `kelvin-ai-docs/docs-ai/agents.md` for detailed query strategies.

## API Conventions

- Base path: `/api/v4`
- List endpoints use `/list` suffix (e.g., `/api/v4/assets/list`)
- Response data in `data` key (not `items`). Parse with `.get('data', [])`
- Delete/update are POST (not HTTP DELETE/PUT): `POST /assets/{name}/delete`
- Get endpoints use `/get` suffix: `GET /assets/{name}/get`
- Datastream list is POST (not GET)
- Pagination: `page_size=200`, check `pagination.next_page`
- Auth: `Authorization: Bearer <token>`

## Common Issues and Solutions

| Symptom | Likely Cause | Diagnostic Steps |
|---------|-------------|-----------------|
| App not producing data | Check logs first | `kelvin workload logs` → look for tracebacks, connection errors |
| "No current session" | Not authenticated | `kelvin auth login` or `scripts/auth-dialog.py` |
| 401 Unauthorized | Token expired | Re-run `kelvin auth login` |
| CrashLoopBackOff | App crashing on startup | `cluster-debug logs <pod>` → check startup errors, missing deps, bad config |
| OOMKilled | Memory limit too low | `cluster-debug kubectl describe pod <name>` → check resource limits |
| Data gaps | Workload stopped or restarted | Query ClickHouse hourly counts → correlate gaps with workload events |
| Stale data | Edge cluster unreachable | `tools/clusters.py list` → check cluster status and `last_seen` |
| "Asset type not found" | Missing prerequisite | `tools/assets.py list-types` → create type before creating assets |
| `legacy_error` | Old platform version | Some API endpoints unavailable; fall back to cluster-debug kubectl |
| Grafana auth fails | Cookie expired or bad creds | Re-run `scripts/auth-dialog.py` to refresh Keycloak credentials |

## Key Rules

- **NEVER use interactive scripts** — they hang in AI agent environments.
- **ALWAYS use the venv** — `source venv/bin/activate` or `venv/bin/python`, `venv/bin/kelvin`.
- **API base path** — `/api/v4` (not `/api/v1`).
- **If the SDK CLI is giving trouble, check if there's an equivalent API call.** The REST API is often simpler. Check `kelvin-ai-docs/docs-ai/api/endpoints/`.
- **SDK version must match the platform.** After login, check for version mismatch warnings (`Current: X Recommended: Y`). If mismatched, install the recommended version: `venv/bin/pip install kelvin-sdk==<recommended>`. Older platforms may need older SDK versions — some newer API endpoints won't exist.
- **Always verify API endpoints against the platform's OpenAPI spec.** After first login to an environment, fetch the spec: `venv/bin/python tools/api_spec.py --env <env> fetch`. Before using any API endpoint, check it exists: `venv/bin/python tools/api_spec.py --env <env> check /assets/list GET`. This prevents calling endpoints that don't exist on older platform versions.
- **ASK before** restarting workloads, deleting resources, or deploying debug pods.
- **Follow the diagnostic methodology** — don't skip steps.

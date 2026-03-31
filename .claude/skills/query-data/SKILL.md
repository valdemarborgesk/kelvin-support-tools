---
name: query-data
description: "Query raw data from ClickHouse or the timeseries API. Use when the user wants to see raw data, run SQL queries, analyze data patterns, or export data."
argument-hint: "<sql or description> on <environment>"
---

# Query Data

Execute data queries — simple ones via REST API, complex ones via ClickHouse (Grafana proxy).

## Steps

1. **Determine the right tool:**
   - Simple (latest value, recent range for one asset/stream): use `tools/timeseries.py`
   - Complex (aggregations, joins, gaps, cross-asset, custom SQL): use `tools/grafana_client.py`

2. **For simple queries:**

```bash
source venv/bin/activate
# Latest value
venv/bin/python tools/timeseries.py --env <env> latest --asset <name> --datastream <ds>

# Time range
venv/bin/python tools/timeseries.py --env <env> query --asset <name> --datastream <ds> --start 24h
```

3. **For ClickHouse queries:**

```bash
venv/bin/python tools/grafana_client.py --env <env> query "<SQL>"
```

4. **Explore the schema:**

```bash
# List all tables
venv/bin/python tools/grafana_client.py --env <env> tables

# Show columns for a table
venv/bin/python tools/grafana_client.py --env <env> schema <table-name>
```

## ClickHouse Reference

Database: `kelvin`

**Timeseries tables:** `timeseries_ad_float`, `timeseries_ad_bool`, `timeseries_ad_string`
- Columns: `timestamp`, `asset_name`, `datastream_name`, `value`, `resource`, `inserted_at`
- **No `cluster_name` column** — filter by `asset_name`

**Platform tables:** `app_workloads`, `assets`, `data_streams`, `clusters`

## Useful Queries

```sql
-- What's flowing right now?
SELECT asset_name, datastream_name, count() as pts, max(timestamp) as latest
FROM kelvin.timeseries_ad_float
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY asset_name, datastream_name ORDER BY pts DESC LIMIT 20

-- Data gaps (hourly buckets)
SELECT toStartOfHour(timestamp) as hour, count() as points
FROM kelvin.timeseries_ad_float
WHERE asset_name = '{asset}' AND datastream_name = '{ds}'
  AND timestamp > now() - INTERVAL 7 DAY
GROUP BY hour ORDER BY hour

-- Compare data rates across assets
SELECT asset_name, count() as pts_1h
FROM kelvin.timeseries_ad_float
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY asset_name ORDER BY pts_1h ASC
```

## Rules

- If the user describes what they want in plain language, translate it to SQL.
- Always use the `kelvin` database prefix (e.g., `kelvin.assets`).
- Present results as clean tables.
- If Grafana auth fails, fall back to REST API timeseries queries.

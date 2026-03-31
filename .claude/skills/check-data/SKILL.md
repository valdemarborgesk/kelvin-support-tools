---
name: check-data
description: "Check if data is flowing for an asset or data stream. Use when the user asks about data flow, data gaps, missing data, stale data, or data quality."
argument-hint: "<asset-name> [datastream] on <environment>"
---

# Check Data Flow

Diagnose data flow issues — is data coming in? Are there gaps? Is it stale?

## Steps

1. **Verify auth:**

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. **List data streams for the asset:**

```bash
venv/bin/python tools/datastreams.py --env <env> list --asset <asset-name>
```

3. **Check latest data point** (quick check via REST API):

```bash
venv/bin/python tools/timeseries.py --env <env> latest --asset <asset-name> --datastream <ds>
```

If recent data exists, data is flowing. If no data, continue.

4. **Check for gaps via ClickHouse** (deep analysis):

```bash
venv/bin/python tools/grafana_client.py --env <env> query "
SELECT datastream_name, max(timestamp) as last_ts, count() as pts_24h
FROM kelvin.timeseries_ad_float
WHERE asset_name = '<asset-name>' AND timestamp > now() - INTERVAL 24 HOUR
GROUP BY datastream_name
ORDER BY last_ts
"
```

5. **Check hourly distribution** (spot gaps):

```bash
venv/bin/python tools/grafana_client.py --env <env> query "
SELECT toStartOfHour(timestamp) as hour, count() as points
FROM kelvin.timeseries_ad_float
WHERE asset_name = '<asset-name>' AND datastream_name = '<ds>'
  AND timestamp > now() - INTERVAL 7 DAY
GROUP BY hour ORDER BY hour
"
```

6. **Diagnose the cause:**
   - **No data at all** → check if the producing workload is running (`kelvin workload list`)
   - **Data stopped at a specific time** → check workload logs around that time
   - **Intermittent gaps** → check cluster health, edge connectivity
   - **Data exists but looks wrong** → check data stream config, compare values across assets

7. **Compare with other assets** (is it just this one?):

```bash
venv/bin/python tools/grafana_client.py --env <env> query "
SELECT asset_name, count() as pts_1h
FROM kelvin.timeseries_ad_float
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY asset_name ORDER BY pts_1h ASC LIMIT 20
"
```

## Rules

- Always start with the quick REST API check before querying ClickHouse.
- If ClickHouse is unavailable (Grafana auth fails), fall back to REST API timeseries queries.
- Report findings clearly: "Data is flowing (last point 2 minutes ago)" or "No data in the last 24 hours — the workload stopped at 3pm yesterday".

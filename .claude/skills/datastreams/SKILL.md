---
name: datastreams
description: "Manage Kelvin data streams via REST API. Use when the user wants to create, list, check, or delete data streams."
argument-hint: "list|get|create|delete [stream-name] on <environment>"
---

# Kelvin Data Streams

Manage data streams via the REST API.

## Steps

1. Verify auth:

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. Determine the operation:

**List data streams** (optionally filter by asset):
```bash
venv/bin/python tools/datastreams.py --env <env> list [--asset <asset-name>]
```

**Get data stream details:**
```bash
venv/bin/python tools/datastreams.py --env <env> get <name>
```

**Create data stream:**
```bash
venv/bin/python tools/datastreams.py --env <env> create --name <n> --title <t> --data-type <boolean|number|string|object> [--semantic-type <measurement|computed|set_point|data_quality>] [--unit <unit>] [--asset <asset-name>]
```

**Delete data stream** (ASK before executing):
```bash
venv/bin/python tools/datastreams.py --env <env> delete <name>
```

## Data Types

- `boolean` — true/false values
- `number` — numeric measurements (temperature, pressure, flow rate)
- `string` — text values (status, labels)
- `object` — complex structured data (JSON)

## Semantic Types

- `measurement` — raw sensor data
- `computed` — derived/calculated values
- `set_point` — target values for control
- `data_quality` — quality scores

## Rules

- ALWAYS use the venv.
- ASK before deleting.
- When creating data streams for an app, match the names to the app's `app.yaml` input/output definitions.

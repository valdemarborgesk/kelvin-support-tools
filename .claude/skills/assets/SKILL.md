---
name: assets
description: "Manage Kelvin assets and asset types via REST API. Use when the user wants to create, list, update, or delete assets or asset types."
argument-hint: "list|get|create|delete [asset-name] on <environment>"
---

# Kelvin Assets

Manage assets and asset types via the REST API.

## Steps

1. Verify auth — check that a valid token exists:

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. Determine the operation from user intent:

**List assets:**
```bash
venv/bin/python tools/assets.py --env <env> list [--type <asset-type>] [--search <term>]
```

**Get asset details:**
```bash
venv/bin/python tools/assets.py --env <env> get <name>
```

**Create asset** (check that asset type exists first):
```bash
venv/bin/python tools/assets.py --env <env> create --name <n> --title <t> --asset-type <at>
```

**Delete asset** (ASK before executing):
```bash
venv/bin/python tools/assets.py --env <env> delete <name>
```

**List asset types:**
```bash
venv/bin/python tools/assets.py --env <env> list-types
```

**Create asset type:**
```bash
venv/bin/python tools/assets.py --env <env> create-type --name <n> --title <t>
```

3. For create: verify the asset type exists first. If not, offer to create it.
4. For delete: always ask for confirmation before executing.

## Rules

- ALWAYS use the venv.
- Asset types must exist before creating assets of that type.
- Asset names must be unique within the environment.
- ASK before deleting.

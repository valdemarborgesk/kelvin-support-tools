---
name: grafana-alerts
description: "Check and manage Grafana alert rules. Use when the user asks about alerts, alert rules, monitoring, or Grafana."
argument-hint: "list|get <uid> on <environment>"
---

# Grafana Alerts

Inspect Grafana alert rules via the Grafana API. Authenticated through Keycloak OAuth.

## Steps

1. **Verify auth** — Grafana uses Keycloak credentials (same as the platform).

2. **List alert rules:**

```bash
source venv/bin/activate
venv/bin/python tools/grafana_client.py --env <env> alerts list
```

3. **Get alert rule details:**

```bash
venv/bin/python tools/grafana_client.py --env <env> alerts get <uid>
```

4. Help the user understand the alert conditions — explain thresholds, query expressions, and evaluation intervals in plain terms.

## Rules

- ALWAYS use the venv.
- If Grafana auth fails, the Keycloak credentials may need refreshing. Run `scripts/auth-dialog.py` again.
- This is read-only by default. Don't modify alert rules without explicit user permission.

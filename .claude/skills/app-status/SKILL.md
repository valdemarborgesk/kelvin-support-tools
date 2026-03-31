---
name: app-status
description: "Check workload health and deployment status. Use when the user asks about app status, what's running, workload health, or deployment state."
argument-hint: <workload-name | all>
---

# App Status

Check the status of deployed Kelvin workloads.

## Steps

1. Verify auth:

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. For a **specific workload**:

```bash
kelvin workload show <name>
```

Show: status, app name, app version, cluster, node, last updated.

3. For **all workloads**:

```bash
kelvin workload list
```

Present as a clean table. Highlight any workloads in error, failed, or stopped state.

4. If the user asks about a specific app (not workload), search by app name:

```bash
kelvin workload search --app-name <app-name>
```

## Rules

- ALWAYS use the venv.
- If status shows errors, suggest checking logs with `/app-logs <name>`.

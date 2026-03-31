---
name: workload-lifecycle
description: "Start, stop, restart, or undeploy a Kelvin workload. Use when the user wants to start, stop, restart, remove, or manage the lifecycle of a deployed workload."
argument-hint: "start|stop|restart|undeploy <workload-name>"
---

# Workload Lifecycle

Manage the lifecycle of deployed workloads without redeploying.

## Steps

1. Verify auth:

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. Determine the operation:

**Start a stopped workload:**
```bash
kelvin workload start <workload-name>
```

**Stop a running workload:**
```bash
kelvin workload stop <workload-name>
```

**Restart a workload** (stop then start):
```bash
kelvin workload stop <workload-name>
# Wait a few seconds
kelvin workload start <workload-name>
```

**Undeploy** (completely remove — ASK before executing):
```bash
kelvin workload undeploy <workload-name>
```

3. After any lifecycle change, verify the new state:

```bash
kelvin workload show <workload-name>
```

## When to Use

- **Start** — after a stop, or when a workload was deployed in stopped state
- **Stop** — to pause a workload without removing it (preserves config)
- **Restart** — when the app is stuck, consuming too much memory, or after a config change
- **Undeploy** — to completely remove a workload and free resources

## Rules

- ALWAYS use the venv.
- **ASK before undeploy** — it permanently removes the workload.
- Stop/start don't require confirmation (non-destructive, reversible).
- After restart, check logs to verify the app started correctly: `kelvin workload logs <name> --tail-lines 20`.

---
name: app-logs
description: "View workload logs for a deployed Kelvin app. Use when the user wants to see logs, check for errors, debug a running app, or troubleshoot a deployment."
argument-hint: <workload-name> [--tail N]
---

# App Logs

View logs from a deployed Kelvin workload.

## Steps

1. Verify auth:

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. Fetch logs:

```bash
kelvin workload logs <workload-name> --tail-lines <N>
```

Default to `--tail-lines 100` if the user doesn't specify.

3. If the workload is not found, list available workloads:

```bash
kelvin workload list
```

4. Analyze the logs for errors, exceptions, or issues. Highlight:
   - Python tracebacks
   - Connection errors (NATS, API, database)
   - Permission/auth failures
   - Data stream or asset not found errors

## Rules

- ALWAYS use the venv.
- If logs are empty, check if the workload is started: `kelvin workload show <name>`.
- If the workload status is `stopped`, suggest: `kelvin workload start <name>`.

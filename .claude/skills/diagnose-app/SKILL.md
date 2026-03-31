---
name: diagnose-app
description: "Diagnose why a Kelvin app or workload isn't working. Use when the user reports an app issue, crash, error, or unexpected behavior."
argument-hint: "<workload-name> on <environment>"
---

# Diagnose App

Systematic troubleshooting for Kelvin SmartApp issues. Follow the diagnostic methodology — don't skip steps.

## Steps

1. **Identify the workload and environment.** If the user didn't specify, ask. If they give an app name instead of workload name, search for it:

```bash
source venv/bin/activate
kelvin workload search --app-name <app-name>
```

2. **Check workload status:**

```bash
kelvin workload show <workload-name>
```

Look at: status (running/stopped/failed), cluster, node, app version, last updated. If stopped or failed, that's the answer — report it and suggest restarting.

3. **Check logs (last 200 lines):**

```bash
kelvin workload logs <workload-name> --tail-lines 200
```

Analyze for:
- Python tracebacks (ImportError, TypeError, ConnectionError, etc.)
- NATS connection errors ("no responders", "timeout")
- Auth errors (401, "unauthorized")
- Data stream errors ("datastream not found", "asset not found")
- OOM or resource errors
- Restart indicators (repeated startup messages)

4. **Check data flow** — is the app receiving data? Is it producing output?

```bash
venv/bin/python tools/datastreams.py --env <env> list --asset <relevant-asset>
venv/bin/python tools/timeseries.py --env <env> latest --asset <asset> --datastream <input-ds>
venv/bin/python tools/timeseries.py --env <env> latest --asset <asset> --datastream <output-ds>
```

5. **Check cluster/node health** if the above looks fine:

```bash
venv/bin/python tools/clusters.py --env <env> get <cluster-name>
```

If the cluster is unreachable, that explains everything.

6. **Deep dive** — if still unclear, use cluster-debug for pod-level inspection:

```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl get pods -n kelvin | grep <workload>
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl describe pod <pod-name> -n kelvin
```

Look for: CrashLoopBackOff, OOMKilled, ImagePullBackOff, resource limits.

7. **Report findings** — summarize what you found and suggest next steps.

## Rules

- Follow the steps in order. Don't jump to cluster-debug before checking logs.
- If the workload doesn't exist, list all workloads to help the user find it.
- ASK before restarting workloads.
- Check platform docs (`kelvin-ai-docs/`) if you encounter unfamiliar errors.

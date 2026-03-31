---
name: cluster-debug
description: "Run remote kubectl, exec, or logs commands on a Kelvin edge cluster. Use when the user needs pod-level inspection, remote commands, or host-level debugging."
argument-hint: "<environment> <cluster> <subcommand> [args]"
---

# Cluster Debug

Remote command execution on Kelvin edge clusters via the shell/exec API (proxied through NATS/edge-updater). No SSH required.

## Subcommands

**kubectl** — run any kubectl command:
```bash
source venv/bin/activate
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl get pods -A
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl describe pod <pod> -n kelvin
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl get events -n kelvin --sort-by=.lastTimestamp
```

**logs** — fetch pod logs:
```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> logs <pod-name> -n kelvin --tail 100
```

**exec** — arbitrary shell command:
```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "df -h"
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "free -h"
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "ps aux | head -20"
```

**deploy-debug** — deploy privileged debug pod (ASK first):
```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> deploy-debug
```

**host** — host-level command via nsenter (needs debug pod):
```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> host "uname -a"
venv/bin/python tools/cluster_debug.py --env <env> <cluster> host "top -bn1 | head -20"
```

**cleanup** — delete the debug pod:
```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> cleanup
```

## Rules

- ALWAYS use the venv.
- ASK before deploying debug pods or running destructive commands.
- If 401 unauthorized, re-authenticate with `/kelvin-login`.
- If cluster not found (404), check cluster name with `tools/clusters.py --env <env> list`.
- Cluster names can be unexpected — if the user gives a partial name, search for it.

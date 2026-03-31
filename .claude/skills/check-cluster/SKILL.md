---
name: check-cluster
description: "Check cluster and node health. Use when the user asks about cluster issues, node problems, connectivity, or infrastructure health."
argument-hint: "<cluster-name> on <environment>"
---

# Check Cluster Health

Diagnose cluster and node health issues.

## Steps

1. **Verify auth:**

```bash
source venv/bin/activate
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

2. **Check cluster status via API:**

```bash
venv/bin/python tools/clusters.py --env <env> get <cluster-name>
```

Look at: status (online/unreachable/pending_provision), last_seen, version.

3. **Check node health:**

```bash
venv/bin/python tools/clusters.py --env <env> nodes <cluster-name>
```

4. **If cluster is online, check pods via remote kubectl:**

```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl get pods -A
```

Look for: CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending, Evicted.

5. **Check specific problem pods:**

```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl describe pod <pod> -n <namespace>
```

6. **Check system resources:**

```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "df -h"
venv/bin/python tools/cluster_debug.py --env <env> <cluster> exec "free -h"
```

7. **Check edge-updater logs** (the agent that manages the cluster):

```bash
venv/bin/python tools/cluster_debug.py --env <env> <cluster> kubectl logs -n kelvin -l app=edge-updater --tail 50
```

## Rules

- If the cluster is unreachable, tell the user — there's nothing we can do remotely.
- ASK before deploying debug pods (`deploy-debug`).
- Don't delete or restart system pods without explicit user permission.

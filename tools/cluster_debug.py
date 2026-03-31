#!/usr/bin/env python3
"""
Remote cluster debug tool.

Route kubectl / exec commands through the Kelvin api-orchestration shell/exec
endpoint — which proxies over NATS to edge-updater on the customer cluster.
Routes commands through the Kelvin API — no SSH required.

Usage:
    python cluster_debug.py --env <env-name> <cluster> <subcommand> [args]
    python cluster_debug.py --url <base-url>  <cluster> <subcommand> [args]

Subcommands:
    kubectl <args...>              Run kubectl command on cluster
    exec <cmd...>                  Run arbitrary sh -c command
    logs <pod> [-n ns] [--tail N]  Fetch pod logs
    deploy-debug                   Deploy privileged kelvin-debug pod
    host <cmd...>                  Run host-level command via nsenter
    shell                          Interactive REPL (local only)
    cleanup                        Delete kelvin-debug pod
"""

import sys
import os
import json
import base64
import argparse
import subprocess
from pathlib import Path

import requests

# ── Constants ──────────────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

IS_NONINTERACTIVE = os.environ.get("NONINTERACTIVE") == "true"

# edge-updater ships kubectl as a symlink at /kelvin/app/kubectl, which is not
# in the default shell PATH. Prepend it so all kubectl calls resolve correctly.
KUBECTL = "PATH=/kelvin/app:$PATH kubectl"

DEBUG_POD_MANIFEST = """
apiVersion: v1
kind: Pod
metadata:
  name: kelvin-debug
  namespace: kelvin
spec:
  hostPID: true
  hostNetwork: true
  tolerations:
  - operator: Exists
  containers:
  - name: debug
    image: alpine
    command: ["sleep", "infinity"]
    securityContext:
      privileged: true
    volumeMounts:
    - name: host-root
      mountPath: /host
  volumes:
  - name: host-root
    hostPath:
      path: /
""".strip()

# ── Config / URL resolution ────────────────────────────────────────────────────

def load_env_config():
    """Parse .ai/config.json, return name→url dict (with https:// prefix)."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        data = json.load(f)
    result = {}
    for env in data.get("environments", []):
        name = env.get("name")
        url = env.get("url", "")
        if name and url:
            if not url.startswith("http"):
                url = f"https://{url}"
            result[name] = url
    return result


def get_base_url(args):
    """Resolve base URL: env var → --url flag → --env lookup in config."""
    # 1. KELVIN_BASE_URL env var
    base = os.environ.get("KELVIN_BASE_URL")
    if base:
        return base.rstrip("/")

    # 2. --url flag (full URL passed directly)
    if getattr(args, "url", None):
        return args.url.rstrip("/")

    # 3. --env name resolved from .ai/config.json
    if getattr(args, "env", None):
        env_map = load_env_config()
        url = env_map.get(args.env)
        if url:
            return url
        print(f"❌ Unknown environment: {args.env}", file=sys.stderr)
        print(
            f"   Known: {', '.join(sorted(env_map.keys()))}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "❌ No environment specified. Use --env, --url, or set KELVIN_BASE_URL.",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Authentication ─────────────────────────────────────────────────────────────

def _get_token_via_kelvin_cli():
    """Try `kelvin auth token` subprocess (local only, after kelvin auth login).

    The SDK writes log lines to stdout alongside the token, so we filter
    for the line that is actually a JWT (starts with 'ey').
    """
    try:
        result = subprocess.run(
            ["kelvin", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            jwt_lines = [l for l in result.stdout.splitlines() if l.startswith("ey")]
            if jwt_lines:
                return jwt_lines[-1]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_token_via_keycloak(base_url):
    """Keycloak password grant — env var fallback."""
    username = os.environ.get("KEYCLOAK_USERNAME")
    password = os.environ.get("KEYCLOAK_PASSWORD")
    if not username or not password:
        return None
    token_url = f"{base_url}/auth/realms/kelvin/protocol/openid-connect/token"
    try:
        r = requests.post(
            token_url,
            data={
                "client_id": "kelvin-client",
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            timeout=15,
        )
        if r.ok:
            return r.json().get("access_token")
        print(
            f"⚠️  Keycloak auth failed: {r.status_code} {r.text[:200]}",
            file=sys.stderr,
        )
    except requests.RequestException as e:
        print(f"⚠️  Keycloak request failed: {e}", file=sys.stderr)
    return None


def get_kelvin_token(base_url):
    """Auth priority chain — returns token or exits with helpful error."""
    # 1. Explicit env var override (works everywhere)
    token = os.environ.get("KELVIN_TOKEN")
    if token:
        return token

    # 2. kelvin auth token CLI (local only)
    token = _get_token_via_kelvin_cli()
    if token:
        return token

    # 3. Keycloak password grant (env var fallback)
    token = _get_token_via_keycloak(base_url)
    if token:
        return token

    # 4. Interactive prompt (local only)
    if not IS_NONINTERACTIVE:
        try:
            import getpass
            print("No token found. Enter your Kelvin bearer token (Ctrl-C to cancel):")
            token = getpass.getpass("Token: ").strip()
            if token:
                return token
        except (KeyboardInterrupt, EOFError):
            print()

    print("❌ Could not obtain a Kelvin token.", file=sys.stderr)
    print("   Options:", file=sys.stderr)
    print("     - Set KELVIN_TOKEN env var", file=sys.stderr)
    print("     - Run: kelvin auth login <url>  (then retry)", file=sys.stderr)
    print(
        "     - Set KEYCLOAK_USERNAME + KEYCLOAK_PASSWORD env vars",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Core API call ──────────────────────────────────────────────────────────────

def shell_exec(base_url, token, cluster, command, timeout=60):
    """POST command to shell/exec endpoint, return output string."""
    url = (
        f"{base_url}/api/v4/orchestration/clusters/{cluster}"
        f"/edge-apps/shell/exec"
    )
    try:
        r = requests.post(
            url,
            json={"command": command},
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {base_url}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)

    if r.status_code == 401:
        print("❌ Unauthorized — token expired or invalid", file=sys.stderr)
        sys.exit(1)
    if r.status_code == 404:
        print(f"❌ Cluster not found: {cluster}", file=sys.stderr)
        sys.exit(1)
    r.raise_for_status()

    try:
        data = r.json()
        return data.get("output") or data.get("result") or str(data)
    except ValueError:
        return r.text


# ── Subcommand implementations ─────────────────────────────────────────────────

def cmd_kubectl(base_url, token, cluster, kubectl_args):
    """Run kubectl <args> via shell/exec."""
    command = KUBECTL + " " + " ".join(kubectl_args)
    print(shell_exec(base_url, token, cluster, command))


def cmd_exec(base_url, token, cluster, cmd_parts):
    """Run arbitrary sh -c <cmd> via shell/exec."""
    user_cmd = " ".join(cmd_parts)
    command = f"sh -c {json.dumps(user_cmd)}"
    print(shell_exec(base_url, token, cluster, command))


def cmd_logs(base_url, token, cluster, args):
    """kubectl logs shortcut."""
    parts = [KUBECTL, "logs"]
    if args.namespace:
        parts += ["-n", args.namespace]
    parts.append(args.pod)
    if args.tail is not None:
        parts.append(f"--tail={args.tail}")
    print(shell_exec(base_url, token, cluster, " ".join(parts)))


def cmd_deploy_debug(base_url, token, cluster):
    """Apply privileged debug pod manifest via kubectl apply."""
    manifest_b64 = base64.b64encode(DEBUG_POD_MANIFEST.encode()).decode()
    command = f"echo '{manifest_b64}' | base64 -d | {KUBECTL} apply -f -"
    print(shell_exec(base_url, token, cluster, command, timeout=90))
    print(
        "Debug pod deploying — wait ~15s, then use: "
        f"cluster_debug.py ... {cluster} host 'uname -a'"
    )


def cmd_host(base_url, token, cluster, cmd_parts):
    """Run command on host via nsenter through kelvin-debug pod."""
    host_cmd = " ".join(cmd_parts)
    command = (
        f"{KUBECTL} exec kelvin-debug -n kelvin -- "
        f"nsenter -t 1 -m -u -i -n -p -- {host_cmd}"
    )
    print(shell_exec(base_url, token, cluster, command, timeout=120))


def cmd_cleanup(base_url, token, cluster):
    """Delete the kelvin-debug pod."""
    command = f"{KUBECTL} delete pod kelvin-debug -n kelvin --ignore-not-found"
    print(shell_exec(base_url, token, cluster, command))


def cmd_shell(base_url, token, cluster):
    """Interactive REPL loop (local only)."""
    if IS_NONINTERACTIVE:
        print(
            "❌ Interactive shell is not available in non-interactive mode.",
            file=sys.stderr,
        )
        print(
            "   Use kubectl, exec, logs, host, or other non-interactive subcommands.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Connected to cluster: {cluster}  (type 'exit' or Ctrl-D to quit)")
    while True:
        try:
            line = input(f"[{cluster}]$ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        output = shell_exec(base_url, token, cluster, line)
        print(output)


# ── Argument parsing / dispatch ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remote cluster debug — route commands via Kelvin shell/exec",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s --env myenv mycluster kubectl get pods -A
  %(prog)s --url https://myenv.kelvin.ai mycluster logs my-pod -n app --tail 50
  %(prog)s --env myenv mycluster deploy-debug
  %(prog)s --env myenv mycluster host 'uname -a'
  %(prog)s --env myenv mycluster shell
  %(prog)s --env myenv mycluster cleanup

  # With explicit token:
  KELVIN_TOKEN=... KELVIN_BASE_URL=... %(prog)s mycluster kubectl get nodes
        """,
    )

    env_group = parser.add_mutually_exclusive_group()
    env_group.add_argument(
        "--env", metavar="ENV", help="Environment name from .ai/config.json"
    )
    env_group.add_argument(
        "--url", metavar="URL", help="Full base URL (e.g. https://myenv.kelvin.ai)"
    )

    parser.add_argument("cluster", help="Cluster name")

    subparsers = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    subparsers.required = True

    # kubectl
    p_kube = subparsers.add_parser("kubectl", help="Run kubectl command on cluster")
    p_kube.add_argument(
        "kubectl_args",
        nargs=argparse.REMAINDER,
        help="kubectl arguments (e.g. get pods -A)",
    )

    # exec
    p_exec = subparsers.add_parser("exec", help="Run arbitrary shell command")
    p_exec.add_argument(
        "cmd_parts",
        nargs=argparse.REMAINDER,
        metavar="cmd",
        help="Command to run (passed to sh -c)",
    )

    # logs
    p_logs = subparsers.add_parser("logs", help="Fetch pod logs")
    p_logs.add_argument("pod", help="Pod name")
    p_logs.add_argument("-n", "--namespace", default=None, help="Kubernetes namespace")
    p_logs.add_argument(
        "--tail", type=int, default=100, metavar="N", help="Last N lines (default: 100)"
    )

    # deploy-debug
    subparsers.add_parser("deploy-debug", help="Deploy privileged kelvin-debug pod")

    # host
    p_host = subparsers.add_parser(
        "host", help="Run host-level command via nsenter (needs deploy-debug first)"
    )
    p_host.add_argument(
        "cmd_parts",
        nargs=argparse.REMAINDER,
        metavar="cmd",
        help="Command to run on the host",
    )

    # shell
    subparsers.add_parser("shell", help="Interactive REPL (local only)")

    # cleanup
    subparsers.add_parser("cleanup", help="Delete kelvin-debug pod")

    args = parser.parse_args()

    base_url = get_base_url(args)
    token = get_kelvin_token(base_url)

    if args.subcommand == "kubectl":
        cmd_kubectl(base_url, token, args.cluster, args.kubectl_args)
    elif args.subcommand == "exec":
        cmd_exec(base_url, token, args.cluster, args.cmd_parts)
    elif args.subcommand == "logs":
        cmd_logs(base_url, token, args.cluster, args)
    elif args.subcommand == "deploy-debug":
        cmd_deploy_debug(base_url, token, args.cluster)
    elif args.subcommand == "host":
        cmd_host(base_url, token, args.cluster, args.cmd_parts)
    elif args.subcommand == "shell":
        cmd_shell(base_url, token, args.cluster)
    elif args.subcommand == "cleanup":
        cmd_cleanup(base_url, token, args.cluster)


if __name__ == "__main__":
    main()

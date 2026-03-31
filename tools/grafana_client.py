#!/usr/bin/env python3
"""Grafana client with ClickHouse proxy and alert rule management.

Authenticates to Grafana via Keycloak OAuth, then queries ClickHouse through
the Grafana datasource proxy. No separate ClickHouse credentials needed.

Usage:
    python tools/grafana_client.py --env beta query "SELECT count() FROM kelvin.assets"
    python tools/grafana_client.py --env beta tables
    python tools/grafana_client.py --env beta schema assets
    python tools/grafana_client.py --env beta alerts list
    python tools/grafana_client.py --env beta alerts get <uid>
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "config.json"


# ── Environment resolution ──────────────────────────────────────────────────


def resolve_env(env_name: str) -> str:
    """Resolve environment name to base URL (with https://)."""
    if not CONFIG_FILE.exists():
        print(f"ERROR: {CONFIG_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    for env in config.get("environments", []):
        if env["name"] == env_name:
            url = env["url"]
            return url if url.startswith("http") else f"https://{url}"
    available = ", ".join(e["name"] for e in config.get("environments", []))
    print(f"ERROR: Unknown environment '{env_name}'. Available: {available}", file=sys.stderr)
    sys.exit(1)


# ── Keycloak credentials ────────────────────────────────────────────────────


def _get_keycloak_creds() -> tuple:
    """Get Keycloak username/password from env vars, keyring, or SDK keyring.

    Priority:
    1. KEYCLOAK_USERNAME / KEYCLOAK_PASSWORD env vars
    2. System keyring under 'kelvin-support' service
    3. Extract from Kelvin SDK auth session
    """
    user = os.environ.get("KEYCLOAK_USERNAME")
    pw = os.environ.get("KEYCLOAK_PASSWORD")
    if user and pw:
        return user, pw

    try:
        import keyring
        user = keyring.get_password("kelvin-support", "keycloak_username")
        pw = keyring.get_password("kelvin-support", "keycloak_password")
        if user and pw:
            return user, pw
    except ImportError:
        pass

    # Try to get credentials from the Kelvin SDK keyring by doing a Keycloak
    # password grant with the SDK's stored refresh token — not implemented yet.
    # For now, fall back to asking the user.
    print("ERROR: Keycloak credentials not found.", file=sys.stderr)
    print("  Set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD env vars,", file=sys.stderr)
    print("  or run: venv/bin/python scripts/auth-dialog.py <url>", file=sys.stderr)
    sys.exit(1)


# ── Grafana OAuth session ───────────────────────────────────────────────────


def grafana_session(base_url: str) -> requests.Session:
    """Return a requests.Session authenticated against Grafana via Keycloak OAuth.

    4-step flow:
    1. GET /grafana/login/generic_oauth → redirects to Keycloak
    2. GET Keycloak login page → parse form action URL
    3. POST credentials to form action → returns redirect
    4. GET redirect URL → sets grafana_session cookie
    """
    user, pw = _get_keycloak_creds()
    s = requests.Session()

    # Step 1: kick off OAuth flow
    r = s.get(f"{base_url}/grafana/login/generic_oauth", allow_redirects=False, timeout=15)
    if "Location" not in r.headers:
        print("ERROR: Grafana did not redirect to Keycloak", file=sys.stderr)
        sys.exit(1)

    # Step 2: load Keycloak login page
    r2 = s.get(r.headers["Location"], allow_redirects=False, timeout=15)

    # Step 3: submit credentials
    m = re.search(r'action="([^"]+)"', r2.text)
    if not m:
        print("ERROR: Could not find Keycloak login form action URL", file=sys.stderr)
        sys.exit(1)
    action_url = m.group(1).replace("&amp;", "&")
    r3 = s.post(
        action_url,
        data={"username": user, "password": pw, "credentialId": ""},
        allow_redirects=False,
        timeout=15,
    )

    # Step 4: follow redirect back to Grafana
    s.get(r3.headers["Location"], allow_redirects=True, timeout=15)

    if "grafana_session" not in s.cookies:
        print("ERROR: Grafana authentication failed — grafana_session cookie not set", file=sys.stderr)
        sys.exit(1)

    return s


def grafana_api(session: requests.Session, base_url: str, method: str, path: str, **kwargs):
    """Call Grafana API and return response."""
    url = f"{base_url}/grafana/api{path}"
    r = session.request(method, url, timeout=30, **kwargs)
    if not r.ok:
        print(f"ERROR: {method} {path} → {r.status_code}: {r.text[:300]}", file=sys.stderr)
        sys.exit(1)
    return r


# ── ClickHouse datasource discovery ─────────────────────────────────────────


def _find_clickhouse_datasource(session: requests.Session, base_url: str) -> dict:
    """Find the ClickHouse datasource in Grafana."""
    r = grafana_api(session, base_url, "GET", "/datasources")
    datasources = r.json()
    for ds in datasources:
        if "clickhouse" in ds.get("type", "").lower():
            return ds
    print("ERROR: No ClickHouse datasource found in Grafana", file=sys.stderr)
    sys.exit(1)


# ── ClickHouse query via Grafana proxy ──────────────────────────────────────
# NOTE: Uses POST /grafana/api/ds/query (Grafana's unified query endpoint),
# NOT /datasources/proxy/uid/<uid>/ (direct proxy returns 502 on ClickHouse).
# The format field must be an integer (1 = table), not a string.


def query_clickhouse(session: requests.Session, base_url: str, sql: str, ds_uid: str = None) -> list:
    """Execute a ClickHouse SQL query via Grafana's ds/query endpoint.

    Returns list of dicts (rows with column names as keys).
    """
    if not ds_uid:
        ds = _find_clickhouse_datasource(session, base_url)
        ds_uid = ds["uid"]

    sql_stripped = sql.strip().rstrip(";")

    body = {
        "queries": [{
            "datasource": {"uid": ds_uid, "type": "grafana-clickhouse-datasource"},
            "rawSql": sql_stripped,
            "format": 1,  # table format
            "refId": "A",
        }],
        "from": "now-1h",
        "to": "now",
    }

    r = grafana_api(session, base_url, "POST", "/ds/query", json=body)
    data = r.json()

    # Parse Grafana data frame response into rows
    frames = data.get("results", {}).get("A", {}).get("frames", [])
    if not frames:
        return []

    frame = frames[0]
    fields = frame.get("schema", {}).get("fields", [])
    values = frame.get("data", {}).get("values", [])

    if not fields or not values:
        return []

    col_names = [f["name"] for f in fields]
    num_rows = len(values[0]) if values else 0

    rows = []
    for i in range(num_rows):
        row = {}
        for j, col in enumerate(col_names):
            row[col] = values[j][i] if j < len(values) and i < len(values[j]) else None
        rows.append(row)

    return rows


# ── Subcommands ─────────────────────────────────────────────────────────────


def format_rows(rows: list) -> str:
    """Format list of dicts as aligned table."""
    if not rows:
        return "(no results)"
    columns = list(rows[0].keys())
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))

    header = "  ".join(col.ljust(widths[col]) for col in columns)
    separator = "  ".join("-" * widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        lines.append("  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))
    lines.append(f"\n{len(rows)} rows")
    return "\n".join(lines)


def cmd_query(session, base_url, sql):
    rows = query_clickhouse(session, base_url, sql)
    print(format_rows(rows))


def cmd_tables(session, base_url):
    rows = query_clickhouse(session, base_url, "SHOW TABLES FROM kelvin")
    if rows:
        for row in rows:
            print(list(row.values())[0])
    else:
        print("(no tables found)")


def cmd_schema(session, base_url, table):
    rows = query_clickhouse(session, base_url, f"DESCRIBE kelvin.{table}")
    print(format_rows(rows))


def cmd_alerts_list(session, base_url):
    rules = grafana_api(session, base_url, "GET", "/v1/provisioning/alert-rules").json()
    if not rules:
        print("No alert rules found.")
        return
    col = max(len(r["title"]) for r in rules)
    for r in sorted(rules, key=lambda x: x["title"]):
        print(f"{r['title']:<{col}}  {r['uid']}")


def cmd_alerts_get(session, base_url, uid):
    rule = grafana_api(session, base_url, "GET", f"/v1/provisioning/alert-rules/{uid}").json()
    print(json.dumps(rule, indent=2))


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Grafana + ClickHouse client")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--env", help="Environment name from config.json")
    group.add_argument("--url", help="Full base URL")

    sub = parser.add_subparsers(dest="command", required=True)

    # query
    p = sub.add_parser("query", help="Execute ClickHouse SQL query")
    p.add_argument("sql", help="SQL query string")

    # tables
    sub.add_parser("tables", help="List tables in kelvin database")

    # schema
    p = sub.add_parser("schema", help="Show table columns")
    p.add_argument("table", help="Table name")

    # alerts
    p_alerts = sub.add_parser("alerts", help="Manage Grafana alerts")
    alerts_sub = p_alerts.add_subparsers(dest="alerts_command", required=True)
    alerts_sub.add_parser("list", help="List alert rules")
    p_get = alerts_sub.add_parser("get", help="Get alert rule details")
    p_get.add_argument("uid", help="Alert rule UID")

    args = parser.parse_args()

    # Resolve base URL
    if args.url:
        base_url = args.url if args.url.startswith("http") else f"https://{args.url}"
    else:
        base_url = resolve_env(args.env)

    # Authenticate to Grafana
    session = grafana_session(base_url)

    # Dispatch
    if args.command == "query":
        cmd_query(session, base_url, args.sql)
    elif args.command == "tables":
        cmd_tables(session, base_url)
    elif args.command == "schema":
        cmd_schema(session, base_url, args.table)
    elif args.command == "alerts":
        if args.alerts_command == "list":
            cmd_alerts_list(session, base_url)
        elif args.alerts_command == "get":
            cmd_alerts_get(session, base_url, args.uid)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch and query the platform's OpenAPI spec.

The spec is fetched from /api/swagger/openapi.json via Keycloak browser auth
and cached locally. Use this to verify endpoints exist before calling them.

Usage:
    python tools/api_spec.py --env beta fetch          # Download and cache the spec
    python tools/api_spec.py --env beta version         # Show API version
    python tools/api_spec.py --env beta check /assets/list GET  # Check if endpoint exists
    python tools/api_spec.py --env beta search assets   # Search endpoints by keyword
    python tools/api_spec.py --env beta paths           # List all paths
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "config.json"
CACHE_DIR = REPO_ROOT / ".cache" / "api-specs"


def resolve_env(env_name: str) -> str:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    for env in config.get("environments", []):
        if env["name"] == env_name:
            url = env["url"]
            return url if url.startswith("http") else f"https://{url}"
    print(f"ERROR: Unknown environment '{env_name}'", file=sys.stderr)
    sys.exit(1)


def _get_keycloak_creds() -> tuple:
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
    print("ERROR: Keycloak credentials not found.", file=sys.stderr)
    sys.exit(1)


def fetch_openapi_spec(base_url: str) -> dict:
    """Fetch the OpenAPI spec via Keycloak browser auth."""
    user, pw = _get_keycloak_creds()
    s = requests.Session()

    r = s.get(f"{base_url}/api/swagger/openapi.json", allow_redirects=False, timeout=15)
    if r.status_code != 302 or "Location" not in r.headers:
        print("ERROR: Expected redirect to Keycloak", file=sys.stderr)
        sys.exit(1)

    r2 = s.get(r.headers["Location"], allow_redirects=False, timeout=15)
    m = re.search(r'action="([^"]+)"', r2.text)
    if not m:
        print("ERROR: Could not find Keycloak login form", file=sys.stderr)
        sys.exit(1)

    action_url = m.group(1).replace("&amp;", "&")
    r3 = s.post(
        action_url,
        data={"username": user, "password": pw, "credentialId": ""},
        allow_redirects=True,
        timeout=15,
    )

    if r3.status_code != 200:
        print(f"ERROR: Auth failed ({r3.status_code})", file=sys.stderr)
        sys.exit(1)

    return r3.json()


def cache_path(env_name: str) -> Path:
    return CACHE_DIR / f"{env_name}.json"


def load_cached_spec(env_name: str) -> dict:
    p = cache_path(env_name)
    if not p.exists():
        print(f"No cached spec for '{env_name}'. Run: api_spec.py --env {env_name} fetch", file=sys.stderr)
        sys.exit(1)
    with open(p) as f:
        return json.load(f)


def cmd_fetch(env_name: str, base_url: str):
    print(f"Fetching OpenAPI spec from {base_url}...")
    spec = fetch_openapi_spec(base_url)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path(env_name), "w") as f:
        json.dump(spec, f, indent=2)
    version = spec.get("info", {}).get("version", "unknown")
    paths = len(spec.get("paths", {}))
    print(f"Cached: {env_name} — API v{version}, {paths} endpoints")


def cmd_version(env_name: str):
    spec = load_cached_spec(env_name)
    print(spec.get("info", {}).get("version", "unknown"))


def cmd_check(env_name: str, path: str, method: str):
    spec = load_cached_spec(env_name)
    # Normalize: add leading slash, remove /api/v4 prefix if present
    path = path.strip()
    if path.startswith("/api/v4"):
        path = path[7:]
    if not path.startswith("/"):
        path = "/" + path

    paths = spec.get("paths", {})
    if path in paths:
        methods = list(paths[path].keys())
        if method.lower() in methods:
            print(f"OK: {method.upper()} {path} exists")
        else:
            print(f"NOT FOUND: {method.upper()} {path} — available methods: {', '.join(m.upper() for m in methods)}")
            sys.exit(1)
    else:
        # Try fuzzy match
        matches = [p for p in paths if path.rstrip("/") in p]
        if matches:
            print(f"NOT FOUND: {path} — similar paths:")
            for m in matches[:5]:
                print(f"  {list(paths[m].keys())[0].upper():6s} {m}")
        else:
            print(f"NOT FOUND: {path}")
        sys.exit(1)


def cmd_search(env_name: str, keyword: str):
    spec = load_cached_spec(env_name)
    keyword_lower = keyword.lower()
    for path, methods in spec.get("paths", {}).items():
        if keyword_lower in path.lower():
            for method in methods:
                summary = methods[method].get("summary", "")
                print(f"{method.upper():6s} {path}  — {summary}")


def cmd_paths(env_name: str):
    spec = load_cached_spec(env_name)
    for path, methods in sorted(spec.get("paths", {}).items()):
        for method in methods:
            print(f"{method.upper():6s} {path}")


def main():
    parser = argparse.ArgumentParser(description="Kelvin OpenAPI spec tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--env", help="Environment name")
    group.add_argument("--url", help="Full base URL")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="Fetch and cache the OpenAPI spec")
    sub.add_parser("version", help="Show cached API version")

    p = sub.add_parser("check", help="Check if an endpoint exists")
    p.add_argument("path", help="API path (e.g., /assets/list)")
    p.add_argument("method", nargs="?", default="GET", help="HTTP method (default: GET)")

    p = sub.add_parser("search", help="Search endpoints by keyword")
    p.add_argument("keyword", help="Search term")

    sub.add_parser("paths", help="List all API paths")

    args = parser.parse_args()

    env_name = args.env or "custom"
    if args.url:
        base_url = args.url if args.url.startswith("http") else f"https://{args.url}"
    elif args.env:
        base_url = resolve_env(args.env)
    else:
        base_url = None

    if args.command == "fetch":
        cmd_fetch(env_name, base_url)
    elif args.command == "version":
        cmd_version(env_name)
    elif args.command == "check":
        cmd_check(env_name, args.path, args.method)
    elif args.command == "search":
        cmd_search(env_name, args.keyword)
    elif args.command == "paths":
        cmd_paths(env_name)


if __name__ == "__main__":
    main()

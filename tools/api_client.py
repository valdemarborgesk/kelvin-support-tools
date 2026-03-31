"""Shared Kelvin REST API client for developer tools.

Handles authentication, environment resolution, and paginated requests.
All REST API tools import from this module.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.json"
API_BASE = "/api/v4"
DEFAULT_PAGE_SIZE = 200


def load_config():
    """Load environment config from config.json."""
    if not CONFIG_PATH.exists():
        print(f"ERROR: {CONFIG_PATH} not found", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def resolve_env(env_name: str) -> str:
    """Resolve environment name to base URL (with https://)."""
    config = load_config()
    for env in config.get("environments", []):
        if env["name"] == env_name:
            url = env["url"]
            if not url.startswith("http"):
                url = f"https://{url}"
            return url
    available = ", ".join(e["name"] for e in config.get("environments", []))
    if available:
        print(f"ERROR: Unknown environment '{env_name}'. Available: {available}", file=sys.stderr)
    else:
        print(f"ERROR: Unknown environment '{env_name}'. No environments configured yet.", file=sys.stderr)
        print(f"  Use --url <full-url> instead, or add it to config.json.", file=sys.stderr)
    sys.exit(1)


def save_environment(name: str, url: str):
    """Add an environment to config.json (if not already present)."""
    config = load_config()
    clean_url = url.replace("https://", "").replace("http://", "").rstrip("/")
    for env in config.get("environments", []):
        if env["name"] == name or env["url"] == clean_url:
            return
    config.setdefault("environments", []).append({"name": name, "url": clean_url})
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def get_token() -> str:
    """Get Kelvin auth token.

    Priority:
    1. KELVIN_TOKEN env var
    2. kelvin auth token CLI command
    """
    token = os.environ.get("KELVIN_TOKEN", "").strip()
    if token:
        return token

    kelvin_bin = REPO_ROOT / "venv" / "bin" / "kelvin"
    if not kelvin_bin.exists():
        kelvin_bin = "kelvin"

    try:
        result = subprocess.run(
            [str(kelvin_bin), "auth", "token"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("ey"):
                return line.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("ERROR: No valid token. Run: kelvin auth login https://<env-url>", file=sys.stderr)
    sys.exit(1)


def add_common_args(parser: argparse.ArgumentParser):
    """Add --env and --url flags to any argparse parser."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--env", help="Environment name from config.json")
    group.add_argument("--url", help="Full base URL (e.g. https://myenv.kelvin.ai)")


def get_base_url(args) -> str:
    """Get base URL from parsed args (--env or --url)."""
    if args.url:
        url = args.url
        if not url.startswith("http"):
            url = f"https://{url}"
        return url
    return resolve_env(args.env)


class KelvinAPI:
    """REST API client for Kelvin platform."""

    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.session = requests.Session()

    @property
    def token(self) -> str:
        if not self._token:
            self._token = get_token()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url}{API_BASE}/{path}"

    def _handle_response(self, resp: requests.Response):
        if resp.status_code == 401:
            print("ERROR: Unauthorized (token expired). Run: kelvin auth login", file=sys.stderr)
            sys.exit(1)
        if resp.status_code == 404:
            print(f"ERROR: Not found: {resp.url}", file=sys.stderr)
            sys.exit(1)
        if not resp.text.strip():
            return [] if resp.status_code == 200 else {}
        try:
            data = resp.json()
        except ValueError:
            print(f"ERROR: Non-JSON response (status {resp.status_code}): {resp.text[:200]}", file=sys.stderr)
            sys.exit(1)
        if isinstance(data, dict) and data.get("name") == "legacy_error":
            print(f"ERROR: Endpoint not available on this platform version", file=sys.stderr)
            sys.exit(1)
        if resp.status_code >= 400:
            print(f"ERROR ({resp.status_code}): {json.dumps(data, indent=2)}", file=sys.stderr)
            sys.exit(1)
        return data

    def get(self, path: str, params: dict = None) -> dict:
        resp = self.session.get(self._url(path), headers=self._headers(), params=params)
        return self._handle_response(resp)

    def post(self, path: str, json_data: dict = None) -> dict:
        resp = self.session.post(self._url(path), headers=self._headers(), json=json_data)
        return self._handle_response(resp)

    def put(self, path: str, json_data: dict = None) -> dict:
        resp = self.session.put(self._url(path), headers=self._headers(), json=json_data)
        return self._handle_response(resp)

    def delete(self, path: str) -> dict:
        resp = self.session.delete(self._url(path), headers=self._headers())
        return self._handle_response(resp)

    def list_all(self, path: str, params: dict = None, page_size: int = DEFAULT_PAGE_SIZE) -> list:
        """Paginated GET that accumulates all results."""
        all_items = []
        params = dict(params or {})
        params["page_size"] = page_size
        page = 1

        while True:
            params["page"] = page
            data = self.get(path, params=params)
            items = data.get("data", [])
            all_items.extend(items)

            pagination = data.get("pagination", {})
            if not pagination.get("next_page"):
                break
            page += 1

        return all_items

    def list_all_post(self, path: str, body: dict = None, page_size: int = DEFAULT_PAGE_SIZE) -> list:
        """Paginated POST that accumulates all results (for endpoints like datastreams/list)."""
        all_items = []
        body = dict(body or {})
        page = 1

        while True:
            params = {"page_size": page_size, "page": page}
            resp = self.session.post(self._url(path), headers=self._headers(), json=body, params=params)
            data = self._handle_response(resp)
            items = data.get("data", [])
            all_items.extend(items)

            pagination = data.get("pagination", {})
            if not pagination.get("next_page"):
                break
            page += 1

        return all_items


def get_client(args) -> KelvinAPI:
    """Create a KelvinAPI client from parsed args."""
    base_url = get_base_url(args)
    return KelvinAPI(base_url)


def format_table(rows: list, columns: list) -> str:
    """Format a list of dicts as an aligned table."""
    if not rows:
        return "(no results)"

    # Calculate column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, ""))
            widths[col] = max(widths[col], len(val))

    # Header
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    separator = "  ".join("-" * widths[col] for col in columns)
    lines = [header, separator]

    # Rows
    for row in rows:
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        lines.append(line)

    lines.append(f"\nTotal: {len(rows)}")
    return "\n".join(lines)

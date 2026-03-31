#!/usr/bin/env python3
"""Authenticate to Kelvin using native macOS dialogs.

Pops up username/password dialogs, authenticates via the SDK,
and stores tokens in the keyring. No Terminal needed.

Usage:
    venv/bin/python scripts/auth-dialog.py https://myenv.kelvin.ai
"""

import subprocess
import sys
from pathlib import Path


def macos_prompt(message: str, title: str = "Kelvin Login", hidden: bool = False) -> str:
    """Show a native macOS input dialog and return the user's input."""
    hidden_flag = "with hidden answer" if hidden else ""
    script = (
        f'display dialog "{message}" default answer "" {hidden_flag} '
        f'with title "{title}" '
        f'buttons {{"Cancel", "OK"}} default button "OK"'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return ""
        output = result.stdout.strip()
        return output.split("text returned:")[1]
    except (subprocess.TimeoutExpired, IndexError):
        return ""


def main():
    if len(sys.argv) < 2:
        print("Usage: venv/bin/python scripts/auth-dialog.py <kelvin-url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        url = f"https://{url}"

    # Show native macOS dialogs for credentials
    username = macos_prompt("Enter your Kelvin username (email):")
    if not username:
        print("Cancelled or no username provided.")
        sys.exit(1)

    password = macos_prompt("Enter your Kelvin password:", hidden=True)
    if not password:
        print("Cancelled or no password provided.")
        sys.exit(1)

    # Use the SDK to authenticate and store tokens in keyring
    print(f"Authenticating as {username} to {url}...")
    try:
        from kelvin.sdk.services.auth.auth_service import AuthService
        from kelvin.sdk.services.credential_store import CredentialStore
        from kelvin.sdk.services.session import SessionService
        from kelvin.sdk.services.docker import DockerService
        from kelvin.sdk.commands.auth import AuthCommands

        auth_cmd = AuthCommands(
            auth=AuthService(),
            credentials=CredentialStore(),
            session=SessionService(),
            docker=DockerService(),
        )

        result = auth_cmd.login_password(url, username, password)
        print(f"Successfully logged on to {result.url} as {username}")

    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

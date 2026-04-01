#!/usr/bin/env python3
"""Authenticate to Kelvin using native OS dialogs with terminal fallback.

Detects the OS and uses the appropriate GUI prompt:
  - macOS:   osascript (AppleScript dialogs)
  - Windows: PowerShell Get-Credential / InputBox
  - Linux:   zenity (GNOME) or kdialog (KDE)
  - Fallback: terminal input() / getpass()

Usage:
    venv/bin/python scripts/auth-dialog.py https://myenv.kelvin.ai
"""

import getpass
import platform
import shutil
import subprocess
import sys


def _macos_prompt(message: str, title: str = "Kelvin Login", hidden: bool = False) -> str:
    """Show a native macOS input dialog via osascript."""
    hidden_flag = "with hidden answer" if hidden else ""
    script = (
        f'display dialog "{message}" default answer "" {hidden_flag} '
        f'with title "{title}" '
        f'buttons {{"Cancel", "OK"}} default button "OK"'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip().split("text returned:")[1]
    except (subprocess.TimeoutExpired, IndexError):
        return ""


def _windows_prompt(message: str, title: str = "Kelvin Login", hidden: bool = False) -> str:
    """Show a native Windows input dialog via PowerShell."""
    if hidden:
        # Use Get-Credential for password (masks input)
        ps = (
            f'$c = Get-Credential -Message "{message}" -UserName "password"; '
            f'$c.GetNetworkCredential().Password'
        )
    else:
        ps = (
            f'Add-Type -AssemblyName Microsoft.VisualBasic; '
            f'[Microsoft.VisualBasic.Interaction]::InputBox("{message}", "{title}", "")'
        )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _linux_prompt(message: str, title: str = "Kelvin Login", hidden: bool = False) -> str:
    """Show a native Linux input dialog via zenity or kdialog."""
    if shutil.which("zenity"):
        cmd = ["zenity", "--entry", "--title", title, "--text", message]
        if hidden:
            cmd.append("--hide-text")
    elif shutil.which("kdialog"):
        if hidden:
            cmd = ["kdialog", "--title", title, "--password", message]
        else:
            cmd = ["kdialog", "--title", title, "--inputbox", message]
    else:
        return ""  # No GUI available, caller will use terminal fallback
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _terminal_prompt(message: str, hidden: bool = False) -> str:
    """Fallback: prompt in the terminal."""
    try:
        if hidden:
            return getpass.getpass(f"{message} ")
        return input(f"{message} ")
    except (EOFError, KeyboardInterrupt):
        return ""


def prompt(message: str, title: str = "Kelvin Login", hidden: bool = False) -> str:
    """Show an input prompt using the best available method for the current OS."""
    system = platform.system()
    value = ""

    if system == "Darwin":
        value = _macos_prompt(message, title, hidden)
    elif system == "Windows":
        value = _windows_prompt(message, title, hidden)
    elif system == "Linux":
        value = _linux_prompt(message, title, hidden)

    # Fallback to terminal if GUI prompt failed or returned empty
    if not value:
        value = _terminal_prompt(message, hidden)

    return value


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/auth-dialog.py <kelvin-url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith("http"):
        url = f"https://{url}"

    username = prompt("Enter your Kelvin username (email):")
    if not username:
        print("Cancelled or no username provided.")
        sys.exit(1)

    password = prompt("Enter your Kelvin password:", hidden=True)
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

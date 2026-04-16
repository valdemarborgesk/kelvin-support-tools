#!/usr/bin/env python3
"""Cross-platform setup for Kelvin Support Tools.

Works on macOS, Linux, and Windows. Requires Python 3.9+.

Usage:
    python3 scripts/setup.py        (macOS/Linux)
    python scripts\setup.py         (Windows)
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IS_WINDOWS = platform.system() == "Windows"
VENV_DIR = REPO_ROOT / "venv"
VENV_BIN = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")
PIP = VENV_BIN / ("pip.exe" if IS_WINDOWS else "pip")
KELVIN = VENV_BIN / ("kelvin.exe" if IS_WINDOWS else "kelvin")
PYTHON = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")


def check_python():
    v = sys.version_info
    if v < (3, 9):
        print(f"ERROR: Python 3.9+ required (found {v.major}.{v.minor})")
        sys.exit(1)
    print(f"  Python {v.major}.{v.minor} OK")


def create_venv():
    if VENV_DIR.exists():
        print("  venv/ already exists")
    else:
        print("  Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)


def install_deps():
    print("  Installing dependencies...")
    subprocess.run([str(PIP), "install", "-q", "--upgrade", "pip"], check=True)
    req = REPO_ROOT / "requirements.txt"
    if req.exists():
        subprocess.run([str(PIP), "install", "-q", "-r", str(req)], check=True)
    else:
        print("  WARNING: requirements.txt not found")


def configure_windows_keyring():
    """Install keyrings.alt and configure keyring to use file-based storage.

    The Windows Credential Manager has a 2560-byte limit on credential values.
    Kelvin tokens (access + refresh as JSON) often exceed this, causing
    'Failed to store credentials' errors during auth.

    keyrings.alt.file.PlaintextKeyring has no size limit and is read by both
    auth-dialog.py and the kelvin CLI (via keyring.cfg auto-discovery).

    Credentials are stored in plaintext at:
      %LOCALAPPDATA%\\Python Keyring\\keyring_pass.cfg
    """
    import os

    print("  Configuring keyring backend for Windows...")

    # Install keyrings.alt (file-based keyring backend with no size limit)
    result = subprocess.run(
        [str(PIP), "install", "-q", "keyrings.alt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  WARNING: Could not install keyrings.alt — auth may fail for large tokens")
        return

    # Write keyring.cfg so both auth-dialog.py and the kelvin CLI use PlaintextKeyring
    # Windows config path: %APPDATA%\Python Keyring\keyring.cfg
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("  WARNING: APPDATA not set — skipping keyring.cfg write")
        return

    cfg_dir = Path(appdata) / "Python Keyring"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "keyring.cfg"
    cfg_file.write_text(
        "[backend]\ndefault-keyring=keyrings.alt.file.PlaintextKeyring\n",
        encoding="utf-8",
    )
    print(f"  Keyring configured: file-based backend (no size limit)")


def check_kelvin():
    try:
        result = subprocess.run(
            [str(KELVIN), "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            ver = result.stdout.strip().splitlines()[0]
            print(f"  Kelvin SDK: {ver}")
        else:
            print("  WARNING: kelvin CLI not available (SDK install may have failed)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  WARNING: kelvin CLI not available (SDK install may have failed)")


def check_docs():
    docs = REPO_ROOT / "docs"
    if docs.is_dir():
        print("  Platform docs: available")
    else:
        print("  WARNING: docs/ directory not found")


def check_docker():
    if not shutil.which("docker"):
        print("  NOTE: Docker not found (optional, needed for app build/test)")
        return
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            print("  Docker: available")
        else:
            print("  NOTE: Docker not running (optional, needed for app build/test)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  NOTE: Docker not running (optional, needed for app build/test)")


def main():
    print("=== Kelvin Support Tools Setup ===")
    os.chdir(REPO_ROOT)

    check_python()
    create_venv()
    install_deps()
    if IS_WINDOWS:
        configure_windows_keyring()
    check_kelvin()
    check_docs()
    check_docker()

    activate = str(VENV_BIN / "activate")
    if IS_WINDOWS:
        activate_cmd = f"  {VENV_BIN}\\activate"
    else:
        activate_cmd = f"  source {activate}"

    print()
    print("Setup complete! Next steps:")
    print(activate_cmd)
    print("  kelvin auth login https://<env-url>")
    print()
    print("See AGENTS.md for the full troubleshooting guide.")


if __name__ == "__main__":
    main()

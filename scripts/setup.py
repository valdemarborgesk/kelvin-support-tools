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
        print(f"ERROR: Python {v.major}.{v.minor} is not supported — Python 3.9 or newer is required.")
        print("  Download Python from https://www.python.org/downloads/ and run setup again.")
        sys.exit(1)
    print(f"  Python {v.major}.{v.minor} OK")


def create_venv():
    if VENV_DIR.exists():
        print("  Tools environment already set up.")
    else:
        print("  Setting up tools environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        except subprocess.CalledProcessError:
            print("ERROR: Could not set up the tools environment.")
            print("  Try running setup again. If it keeps failing, restart your terminal first.")
            sys.exit(1)


def install_deps():
    print("  Installing Kelvin packages...")
    try:
        subprocess.run([str(PIP), "install", "-q", "--upgrade", "pip"], check=True)
        req = REPO_ROOT / "requirements.txt"
        if req.exists():
            subprocess.run([str(PIP), "install", "-q", "-r", str(req)], check=True)
        else:
            print("  WARNING: Package list not found — some files may be missing from the download.")
    except subprocess.CalledProcessError:
        print("ERROR: Could not install required packages.")
        print("  Check your internet connection and try running setup again.")
        sys.exit(1)


def configure_windows_login():
    """Configure login credential storage on Windows.

    Windows Credential Manager limits stored values to 2560 bytes.
    Kelvin login tokens often exceed this, causing auth failures.
    This installs a file-based alternative with no size limit.
    """
    print("  Configuring login storage...")

    result = subprocess.run(
        [str(PIP), "install", "-q", "keyrings.alt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  WARNING: Login storage setup failed — you may see errors when logging in.")
        return

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        print("  WARNING: Could not configure login storage — you may see errors when logging in.")
        return

    cfg_dir = Path(appdata) / "Python Keyring"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "keyring.cfg"
    cfg_file.write_text(
        "[backend]\ndefault-keyring=keyrings.alt.file.PlaintextKeyring\n",
        encoding="utf-8",
    )
    print("  Login storage configured.")


def check_kelvin():
    try:
        result = subprocess.run(
            [str(KELVIN), "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            ver = result.stdout.strip().splitlines()[0]
            print(f"  Kelvin: {ver}")
        else:
            print("  WARNING: Kelvin tools not found — try running setup again.")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  WARNING: Kelvin tools not found — try running setup again.")


def check_docs():
    docs = REPO_ROOT / "docs"
    if docs.is_dir():
        print("  Platform documentation: available")
    else:
        print("  WARNING: Platform documentation not found.")


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
            print("  NOTE: Docker is not running (optional, needed for app build/test)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  NOTE: Docker is not running (optional, needed for app build/test)")


def main():
    print("=== Kelvin Support Tools Setup ===")
    os.chdir(REPO_ROOT)

    check_python()
    create_venv()
    install_deps()
    if IS_WINDOWS:
        configure_windows_login()
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

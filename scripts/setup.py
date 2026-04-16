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
IS_MAC = platform.system() == "Darwin"
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


def find_python_version(major, minor):
    """Find a specific Python version installed on the system. Returns path or None."""
    v = sys.version_info
    if (v.major, v.minor) == (major, minor):
        return sys.executable

    candidates = []
    if IS_WINDOWS:
        names = [f"python{major}.{minor}", f"python{major}{minor}"]
    else:
        names = [f"python{major}.{minor}"]

    for name in names:
        path = shutil.which(name)
        if path:
            candidates.append(path)

    if IS_WINDOWS:
        py = shutil.which("py")
        if py:
            try:
                result = subprocess.run(
                    [py, f"-{major}.{minor}", "-c", "import sys; print(sys.executable)"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    candidates.append(result.stdout.strip())
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    for path in candidates:
        try:
            result = subprocess.run(
                [path, "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                m, n = map(int, result.stdout.strip().split())
                if (m, n) == (major, minor):
                    return path
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            continue

    return None


def install_python(major, minor):
    """Install a specific Python version. Returns path to executable."""
    target = f"{major}.{minor}"
    print(f"  Python {target} not found — installing...")

    if IS_MAC:
        if not shutil.which("brew"):
            print("ERROR: Homebrew is not installed.")
            print("  Install it from https://brew.sh, then run setup again.")
            sys.exit(1)
        print(f"  Installing Python {target} via Homebrew (this may take a few minutes)...")
        try:
            subprocess.run(["brew", "install", f"python@{target}"], check=True)
        except subprocess.CalledProcessError:
            print("ERROR: Python installation failed.")
            print("  Check your internet connection and try again, or download Python manually:")
            print("  https://www.python.org/downloads/")
            sys.exit(1)
        path = find_python_version(major, minor)
        if not path:
            brew_prefix = subprocess.run(
                ["brew", "--prefix", f"python@{target}"],
                capture_output=True, text=True,
            ).stdout.strip()
            candidate = Path(brew_prefix) / "bin" / f"python{target}"
            if candidate.exists():
                path = str(candidate)
        if path:
            print(f"  Python {target} installed.")
            return path
        print("ERROR: Python was installed but could not be found.")
        print("  Restart your terminal and run setup again.")
        sys.exit(1)

    elif IS_WINDOWS:
        winget = shutil.which("winget")
        if winget:
            print(f"  Downloading and installing Python {target}...")
            result = subprocess.run(
                ["winget", "install", f"Python.Python.{target}", "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                path = find_python_version(major, minor)
                if path:
                    print(f"  Python {target} installed.")
                    return path
        print(f"ERROR: Could not install Python automatically.")
        print(f"  Please download Python {target} from https://www.python.org/downloads/")
        print("  After installing, run setup again.")
        sys.exit(1)

    else:
        print(f"ERROR: Python {target} is not installed.")
        print(f"  Install it with your package manager:")
        print(f"    Ubuntu/Debian:  sudo apt install python{target} python{target}-venv")
        print(f"    Fedora/RHEL:   sudo dnf install python{target}")
        print("  Then run setup again.")
        sys.exit(1)


def create_venv(python_exe=None):
    if python_exe is None:
        python_exe = sys.executable
    if VENV_DIR.exists():
        print("  Tools environment already set up.")
    else:
        print("  Setting up tools environment...")
        try:
            subprocess.run([python_exe, "-m", "venv", str(VENV_DIR)], check=True)
        except subprocess.CalledProcessError:
            print("ERROR: Could not set up the tools environment.")
            print("  Try running setup again. If it keeps failing, restart your terminal first.")
            sys.exit(1)


def install_deps(retry=False):
    """Install dependencies.

    Returns a (major, minor) tuple if the user wants to retry with a different
    Python version. Returns None on success. Exits on unrecoverable failure.
    """
    print("  Installing Kelvin packages...")

    # Upgrade pip — non-fatal if this fails
    subprocess.run(
        [str(PIP), "install", "-q", "--upgrade", "pip"],
        capture_output=True,
    )

    req = REPO_ROOT / "requirements.txt"
    if not req.exists():
        print("  WARNING: Package list not found — some files may be missing from the download.")
        return None

    result = subprocess.run(
        [str(PIP), "install", "-q", "-r", str(req)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return None  # Success

    # Installation failed
    error = (result.stdout + result.stderr).strip()
    v = sys.version_info
    suggested = (v.major, v.minor - 1)

    if retry:
        print("ERROR: Could not install required packages.")
        if error:
            print()
            print(error)
        sys.exit(1)

    print(f"\n  Could not install packages for Python {v.major}.{v.minor}.")
    print(f"  This sometimes happens when packages don't yet support the latest Python.")
    print()
    print(f"  [1] Try with Python {suggested[0]}.{suggested[1]} instead (recommended)")
    print(f"  [2] Show the error details and exit")
    try:
        choice = input("  Choose [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "2"

    if choice == "1":
        return suggested

    print()
    if error:
        print(error)
        print()
    print("ERROR: Could not install required packages.")
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

    fallback = install_deps()
    if fallback:
        major, minor = fallback
        print(f"\n  Looking for Python {major}.{minor}...")
        fallback_exe = find_python_version(major, minor)
        if not fallback_exe:
            fallback_exe = install_python(major, minor)
        print(f"  Rebuilding tools environment with Python {major}.{minor}...")
        shutil.rmtree(VENV_DIR)
        create_venv(fallback_exe)
        install_deps(retry=True)

    if IS_WINDOWS:
        configure_windows_login()
    check_kelvin()
    check_docs()
    check_docker()

    if IS_WINDOWS:
        activate_cmd = f"  {VENV_BIN}\\activate"
    else:
        activate_cmd = f"  source {VENV_BIN / 'activate'}"

    print()
    print("Setup complete! Next steps:")
    print(activate_cmd)
    print("  kelvin auth login https://<env-url>")
    print()
    print("See AGENTS.md for the full troubleshooting guide.")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Kelvin Support Tools Setup ==="

# Check Python 3.9+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "ERROR: Python 3.9+ required (found $PY_VERSION)"
    exit 1
fi
echo "  Python $PY_VERSION OK"

# Create venv
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
else
    echo "  venv/ already exists"
fi

# Install dependencies
echo "  Installing dependencies..."
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

# Verify kelvin CLI
if venv/bin/kelvin --version &>/dev/null; then
    KELVIN_VER=$(venv/bin/kelvin --version 2>&1 | head -1)
    echo "  Kelvin SDK: $KELVIN_VER"
else
    echo "  WARNING: kelvin CLI not available (SDK install may have failed)"
fi

# Check docs
if [ -d "docs" ]; then
    echo "  Platform docs: available"
else
    echo "  WARNING: docs/ directory not found"
fi

# Check Docker
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    echo "  Docker: available"
else
    echo "  NOTE: Docker not running (optional, needed for app build/test)"
fi

echo ""
echo "Setup complete! Next steps:"
echo "  source venv/bin/activate"
echo "  kelvin auth login https://<env-url>"
echo ""
echo "See AGENTS.md for the full troubleshooting guide."

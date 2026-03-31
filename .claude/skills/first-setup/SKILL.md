---
name: first-setup
description: "First-time setup for Kelvin Dev Tools. Use when the user is new, setting up for the first time, or when the venv is missing."
---

# First-Time Setup

Guided onboarding for new users. Walks through environment setup and first login.

## Steps

### Step 1: Bootstrap the environment

```bash
bash scripts/setup.sh
```

This creates the Python venv, installs the Kelvin SDK, and initializes the docs submodule. Check the output for any warnings (Docker not running, etc.).

If setup.sh fails:
- **"python3 not found"** — Python 3.9+ must be installed. On macOS: `brew install python3`.
- **"pip install failed"** — check internet connection. The Kelvin SDK is downloaded from PyPI.

### Step 2: Activate the environment

```bash
source venv/bin/activate
```

Verify the SDK is working:

```bash
kelvin --version
```

### Step 3: First login

This is the only step that requires user interaction. The Kelvin SDK needs their username and password once — after that, the macOS keyring stores the credentials.

Ask the user which environment they work with. Look up the URL in `config.json`.

Then run the auth dialog — this pops up native macOS windows for credentials (password is masked):

```bash
venv/bin/python scripts/auth-dialog.py https://<resolved-url>
```

Tell the user a login window will appear — they just enter their email and password. The keyring will store the credentials for all future logins.

### Step 4: Verify

After they complete the login:

```bash
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

If a JWT token is returned, everything is set up.

### Step 5: Confirm Docker (optional)

If they plan to build and test apps locally:

```bash
docker info > /dev/null 2>&1 && echo "Docker is running" || echo "Docker is not running — needed for app build/test"
```

### Step 6: Done

Tell the user they're all set. Suggest they try:
- "Create a new app called hello-world"
- "List clusters on beta"
- "What apps are deployed on beta?"

## Rules

- Run each step sequentially — wait for confirmation before proceeding.
- NEVER ask the user to paste credentials into the chat.
- If any step fails, troubleshoot before moving on.
- This skill should also trigger if the venv is missing when any other skill runs.

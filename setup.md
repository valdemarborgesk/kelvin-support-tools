# Kelvin Support Tools — Setup

You are an AI assistant helping a user set up Kelvin Support Tools. Read this entire document before starting. Follow the steps in order.

## Introduction

Start by explaining what you're about to set up. Say this to the user in plain language:

> **Kelvin Support Tools** is a diagnostic toolkit that gives an AI assistant access to your Kelvin environment — logs, data, cluster state, alerts — so it can help you troubleshoot SmartApp and platform issues.
>
> **What gets installed:**
> A folder on your computer containing the Kelvin SDK, a set of diagnostic AI skills, and the platform documentation. Once set up, point your AI tool at that folder and describe the issue you're seeing.
>
> **What you'll need:**
> - An internet connection
> - Your Kelvin username and password
> - Git (we'll check, and help you install it if it's missing)
>
> **We'll also need a folder** to install everything into. You can choose where, or I'll suggest a location.

Then ask:

> **How would you like to proceed?**
>
> 1. **Do it for me** — I'll handle everything automatically with minimal interruptions
> 2. **Walk me through it** — explain each step and ask before proceeding

- **Option 1:** proceed through all steps using sensible defaults, only pausing if a decision is genuinely needed or if a step fails.
- **Option 2:** pause before each step, explain what it does, and wait for confirmation.

## Step 0: Verify you can run commands

**You must be running in an AI coding tool that can execute shell commands** (e.g., Claude Code, Codex, Cursor, Windsurf, or a terminal). If you cannot run commands, tell the user to switch to a mode or tool that supports command execution.

## Step 1: Detect the OS

Run this at the start and remember the result — all later commands depend on it:

```bash
python3 -c "import platform; print(platform.system())" 2>/dev/null || python -c "import platform; print(platform.system())"
```

This returns `Darwin` (macOS), `Linux`, or `Windows`. Remember this as `OS`.

Set these variables based on the OS (use them in all subsequent commands):

| Variable | macOS / Linux | Windows |
|----------|--------------|---------|
| `PYTHON` | `python3` | `python` |
| `VENV_BIN` | `venv/bin` | `venv\Scripts` |
| `ACTIVATE` | `source venv/bin/activate` | `venv\Scripts\activate` |
| `KELVIN` | `venv/bin/kelvin` | `venv\Scripts\kelvin.exe` |
| `VENV_PYTHON` | `venv/bin/python` | `venv\Scripts\python.exe` |
| `VENV_PIP` | `venv/bin/pip` | `venv\Scripts\pip.exe` |

> **IMPORTANT — always activate the venv before running commands.** Never call bare `kelvin`, `python`, or `pip` without activating first. Activate and run in the same command: `<ACTIVATE> && kelvin ...`. If your agent runs each command in a separate shell, chain them: `cd <REPO_PATH> && <ACTIVATE> && kelvin workload list`. Alternatively, use full venv paths: `<REPO_PATH>/<KELVIN>`, `<REPO_PATH>/<VENV_PYTHON>`, etc.

## Step 2: Ask the user about their current state

Before doing anything, ask the user:

> **Is this a fresh install, or have you already set up the Kelvin Support Tools before?**
>
> 1. **Fresh install** — I haven't set anything up yet
> 2. **Already set up** — I've done this before
> 3. **Not sure**

Based on their answer:

- **Fresh install** → go to Step 3
- **Already set up** → ask: **"Where is the kelvin-support-tools folder?"**. Once they give you a path, verify it:

```bash
REPO_PATH="<the path they gave you>"
<PYTHON> -c "
from pathlib import Path
p = Path(r'$REPO_PATH')
print('REPO=ok' if (p / 'AGENTS.md').exists() else 'REPO=not_found')
venv_kelvin = p / '<VENV_BIN>' / 'kelvin'
print('VENV=ok' if venv_kelvin.exists() else 'VENV=missing')
"
```

Then check auth:
```bash
"$REPO_PATH/<VENV_BIN>/kelvin" auth token 2>/dev/null | grep '^ey' | tail -1 && echo "AUTH=ok" || echo "AUTH=not_logged_in"
```

Then skip to the first incomplete step:

| Status | Skip to |
|--------|---------|
| REPO not found | Step 3 |
| REPO ok, VENV missing | Step 4 |
| REPO ok, VENV ok, AUTH not logged in | Step 5 |
| REPO ok, VENV ok, AUTH ok | Step 7 |

- **Not sure** → search for it:

```bash
<PYTHON> -c "from pathlib import Path; [print(p) for p in Path.home().rglob('kelvin-support-tools/AGENTS.md')]"
```

If found, confirm with user. If not found, treat as fresh install.

**IMPORTANT:** Remember the repo location as `REPO_PATH` and use it in every subsequent command.

## Step 3: Prerequisites and clone

Check what's available:

```bash
<PYTHON> -c "
import shutil, sys
for cmd in ['python3', 'python', 'git', 'docker']:
    path = shutil.which(cmd)
    print(f'{cmd}: {path}' if path else f'{cmd}: NOT FOUND')
print(f'Python version: {sys.version}')
"
```

If anything is missing, tell the user what to install and wait:

| Tool | macOS | Linux (Debian/Ubuntu) | Linux (Fedora/RHEL) | Windows |
|------|-------|-----------------------|---------------------|---------|
| Python 3.9+ | `brew install python3` | `sudo apt install python3 python3-venv` | `sudo dnf install python3` | Download from python.org |
| Git | `brew install git` | `sudo apt install git` | `sudo dnf install git` | Download from git-scm.com |

> **Linux note:** The `python3-venv` package is required on Debian/Ubuntu — without it, `python3 -m venv` will fail.

Then clone. Check the current working directory first and ask the user:

> **I'll clone Kelvin Support Tools into the current folder (`<CWD>`). Is that OK, or would you prefer a different location?**

Once confirmed (or the user provides a different path):

```bash
cd <chosen-folder>
git clone git@github.com:valdemarborgesk/kelvin-support-tools.git
```

If SSH fails, try HTTPS:

```bash
git clone https://github.com/valdemarborgesk/kelvin-support-tools.git
```

Set `REPO_PATH` to the full path where it landed (e.g., `<chosen-folder>/kelvin-support-tools`).

## Step 4: Run setup

```bash
cd <REPO_PATH> && <PYTHON> scripts/setup.py
```

## Step 5: First login

Ask the user: **"What is the URL of your Kelvin environment?"** (it looks like `https://something.kelvin.ai` or `https://something.kelvininc.com`)

If they give a short name instead of a URL, try to resolve it from `config.json`:

```bash
<PYTHON> -c "import json; envs={e['name']:e['url'] for e in json.load(open('<REPO_PATH>/config.json')).get('environments',[])}; name='<what-they-said>'; print(f'https://{envs[name]}' if name in envs else 'NOT_FOUND')"
```

If not found, ask them for the full URL.

Run the login dialog — uses native OS dialogs (macOS: AppleScript, Windows: PowerShell, Linux: zenity/kdialog) with terminal fallback:

```bash
<REPO_PATH>/<VENV_PYTHON> <REPO_PATH>/scripts/auth-dialog.py https://<resolved-url>
```

Tell the user a login prompt will appear. After it completes, verify:

```bash
<REPO_PATH>/<KELVIN> auth token 2>/dev/null | grep '^ey' | tail -1
```

## Step 6: Check SDK version compatibility

After login, check if the SDK version matches what the platform recommends:

```bash
<REPO_PATH>/<KELVIN> auth login https://<resolved-url> 2>&1 | grep -i "recommended"
```

If the output shows a version mismatch like `Current: 9.7.3 Recommended: 9.4.4`, install the recommended version:

```bash
<REPO_PATH>/<VENV_PIP> install -q kelvin-sdk==<recommended-version>
```

Then verify:

```bash
<REPO_PATH>/<KELVIN> --version
```

If no mismatch warning appears, the current version is fine — skip this step.

## Step 7: Verify

```bash
<REPO_PATH>/<KELVIN> workload list 2>&1 | head -5
```

## Step 8: Done

Tell the user the exact folder path, then:

> **Setup complete!** Here's how to use it:
>
> 1. Open your AI coding tool
> 2. Point it at **<REPO_PATH>**
> 3. Describe your issue!
>
> Things you can ask:
> - "My app pump-monitor on my environment isn't working"
> - "Is data flowing for beam_pump_01 on my environment?"
> - "What's wrong with cluster my-cluster?"
> - "Show me the logs for my-workload"
> - "Query ClickHouse for data gaps on this asset"
> - "List all pods on my environment-cluster-01"
> - "What are the Grafana alerts on my environment?"

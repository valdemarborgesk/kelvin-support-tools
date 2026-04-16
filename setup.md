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
> 1. **Do it for me** — set everything up automatically, I'll only interrupt if something needs a decision
> 2. **Walk me through it** — tell me what each step does, I'll run the commands myself and you check my progress
> 3. **Show me exactly what gets installed first** — give me a full breakdown before we start

- **Option 1:** proceed through all steps automatically using sensible defaults, only pausing for genuine decisions or failures.
- **Option 2:** for each step, explain what it does and why, then provide the command for the user to run themselves. Wait for them to confirm it worked before moving on.
- **Option 3:** before doing anything, give the user a detailed breakdown of everything that will be installed (see below), then ask whether to proceed with option 1 or 2.

If the user picks **option 3**, explain the following in plain language:

> Here is everything that will be installed:
>
> **1. The repository** — cloned from GitHub into a folder you choose. Contains all the tools, skills, and configuration.
>
> **2. Python virtual environment** — an isolated Python environment just for this toolkit, so nothing interferes with other software on your computer.
>
> **3. Kelvin SDK** — the official Kelvin Python library (version 9.x). This is what lets the AI talk to the Kelvin platform — query logs, check cluster state, inspect data, manage workloads, etc.
>
> **4. Supporting packages** — a set of Python libraries the SDK depends on, plus diagnostic tools for querying ClickHouse and Grafana. All installed automatically.
>
> **5. AI skills** — 14 pre-built diagnostic skills: checking app status, reading logs, querying data, inspecting clusters, running Grafana alert checks, and more.
>
> **6. Platform documentation** — a local copy of Kelvin's API, SDK, and infrastructure docs. The AI reads these to give accurate answers without needing internet access.
>
> **7. Environment configuration** — a list of Kelvin environment URLs (31 environments) so you can refer to environments by name.
>
> Nothing is installed system-wide — everything stays inside the folder we create. You can delete the folder at any time to remove it completely.

Then ask: **"Ready to start? [1] Do it for me / [2] Walk me through it"** and proceed accordingly.

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

If Git is missing, tell the user what to install and wait for them to confirm before continuing:

| Tool | macOS | Linux (Debian/Ubuntu) | Linux (Fedora/RHEL) | Windows |
|------|-------|-----------------------|---------------------|---------|
| Git | `brew install git` | `sudo apt install git` | `sudo dnf install git` | Download from git-scm.com |

> **Python note:** The setup script handles Python automatically — it will find a compatible version or install one if needed.

> **Linux note:** The `python3-venv` package is required on Debian/Ubuntu. The setup script will warn if it's missing: `sudo apt install python3-venv`.

**Docker (optional):** Not required for diagnostics, but needed if the user also wants to build or test apps locally. Check whether it's available:

```bash
docker info 2>&1 | head -3
```

If Docker is not found or not running, note it but do not block setup — continue to the next step.

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

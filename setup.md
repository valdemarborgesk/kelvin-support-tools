# Kelvin Support Tools — Setup

You are setting up a troubleshooting environment for diagnosing Kelvin SmartApp and platform issues. Follow these steps in order. Wait for each step to complete before moving on.

## Step 0: Make sure you are in Code mode

**You MUST be running in Claude Code (CLI or Desktop Code mode) to execute commands.** If you are in a regular Claude Desktop chat, you cannot run bash commands.

If the user is in a regular Claude Desktop chat, tell them:

> To set this up, I need to be able to run commands on your machine. Please:
> 1. Click the **Code** tab at the top of Claude Desktop
> 2. Select **any folder** as the working directory (your home folder is fine)
> 3. Then paste these instructions again or ask me to set up Kelvin Support Tools

Do not proceed until you can execute bash commands.

## Step 1: Ask the user about their current state

Before doing anything, ask the user:

> **Is this a fresh install, or have you already set up the Kelvin Support Tools before?**
>
> 1. **Fresh install** — I haven't set anything up yet
> 2. **Already set up** — I've done this before
> 3. **Not sure**

Based on their answer:

- **Fresh install** → go to Step 2
- **Already set up** → ask: **"Where is the kelvin-support-tools folder?"**. Once they give you a path, verify it:

```bash
REPO_PATH="<the path they gave you>"
[ -f "$REPO_PATH/AGENTS.md" ] && echo "REPO=ok" || echo "REPO=not_found"
[ -x "$REPO_PATH/venv/bin/kelvin" ] && echo "VENV=ok" || echo "VENV=missing"
TOKEN=$("$REPO_PATH/venv/bin/kelvin" auth token 2>/dev/null | grep '^ey' | tail -1)
[ -n "$TOKEN" ] && echo "AUTH=ok" || echo "AUTH=not_logged_in"
```

Then skip to the first incomplete step:

| Status | Skip to |
|--------|---------|
| REPO not found | Step 2 |
| REPO ok, VENV missing | Step 3 |
| REPO ok, VENV ok, AUTH not logged in | Step 4 |
| REPO ok, VENV ok, AUTH ok | Step 6 |

- **Not sure** → search for it:

```bash
find /Users -maxdepth 4 -name "AGENTS.md" -path "*/kelvin-support-tools/*" 2>/dev/null
```

If found, confirm with user. If not found, treat as fresh install.

**IMPORTANT:** Remember the repo location as `REPO_PATH` and use it in every subsequent command.

## Step 2: Prerequisites and clone

Check what's available:

```bash
which python3 && python3 --version
which git && git --version
```

If anything is missing, tell the user what to install and wait:
- **Python 3.9+**: `brew install python3`
- **Git**: `brew install git`

Then clone:

```bash
mkdir -p ~/work && cd ~/work
git clone --recursive git@github.com:kelvininc/kelvin-support-tools.git
```

If SSH fails, try HTTPS:

```bash
git clone --recursive https://github.com/kelvininc/kelvin-support-tools.git
```

Set `REPO_PATH` to wherever it landed.

## Step 3: Run setup

```bash
cd <REPO_PATH> && bash scripts/setup.sh
```

## Step 4: First login

Ask the user: **"What is the URL of your Kelvin environment?"** (it looks like `https://something.kelvin.ai` or `https://something.kelvininc.com`)

If they give a short name instead of a URL, try to resolve it from `config.json`:

```bash
python3 -c "import json; envs={e['name']:e['url'] for e in json.load(open('<REPO_PATH>/config.json')).get('environments',[])}; name='<what-they-said>'; print(f'https://{envs[name]}' if name in envs else 'NOT_FOUND')"
```

If not found, ask them for the full URL.

Run the login dialog — native macOS windows for credentials:

```bash
<REPO_PATH>/venv/bin/python <REPO_PATH>/scripts/auth-dialog.py https://<resolved-url>
```

Tell the user a login dialog will pop up. After it completes, verify:

```bash
source <REPO_PATH>/venv/bin/activate && kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

## Step 5: Check SDK version compatibility

After login, check if the SDK version matches what the platform recommends:

```bash
source <REPO_PATH>/venv/bin/activate && kelvin auth login https://<resolved-url> 2>&1 | grep -i "recommended"
```

If the output shows a version mismatch like `Current: 9.7.3 Recommended: 9.4.4`, install the recommended version:

```bash
<REPO_PATH>/venv/bin/pip install -q kelvin-sdk==<recommended-version>
```

Then verify the new version:

```bash
kelvin --version
```

If no mismatch warning appears, the current version is fine — skip this step.

## Step 6: Verify

```bash
source <REPO_PATH>/venv/bin/activate && kelvin workload list 2>&1 | head -5
```

## Step 7: Done

Tell the user the exact folder path, then:

> **Setup complete!** Here's how to use it:
>
> 1. Open **Claude Desktop**
> 2. Click **Code** → **Select folder** → pick **<REPO_PATH>**
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

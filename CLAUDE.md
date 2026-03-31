# Kelvin Support Tools

Read **[AGENTS.md](AGENTS.md)** for the full troubleshooting guide, diagnostic methodology, and tool reference.

## First Run Check

Before doing anything else, verify the environment is set up:

```bash
test -d venv && venv/bin/kelvin --version 2>/dev/null
```

If the venv doesn't exist or the kelvin CLI is not found, run setup first:

```bash
bash scripts/setup.sh
```

Then activate: `source venv/bin/activate`

## Skills

Skills are in `.claude/skills/`. They activate automatically when matching user intent, or can be invoked explicitly via slash commands.

## Universal Rules

- **NEVER use interactive scripts** — they hang in all environments.
- **ALWAYS use the venv** — `source venv/bin/activate` or `venv/bin/python`, `venv/bin/kelvin`.
- **API base path** — `/api/v4` (not `/api/v1`).
- **ASK before** restarting workloads or deleting resources.
- **Follow the diagnostic methodology** — logs first, then data, then infrastructure.

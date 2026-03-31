---
name: kelvin-login
description: "Authenticate to a Kelvin environment. Use when the user needs to log in, authenticate, or refresh a token for a Kelvin environment."
argument-hint: <env-name-or-url>
---

# Kelvin Login

Authenticate to a Kelvin environment using the SDK CLI.

## Steps

1. Ask the user for their **environment URL** (e.g., `https://myenv.kelvin.ai`). If they give a short name, check `config.json` for a match. If not found, ask for the full URL.

2. Login:

```bash
source venv/bin/activate && kelvin auth login https://<url>
```

3. Verify:

```bash
kelvin auth token 2>/dev/null | grep '^ey' | tail -1
```

If a JWT is returned, auth succeeded.

4. **Save the environment** to config.json so it's available for future `--env` lookups. Derive a short name from the URL (e.g., `myenv` from `myenv.kelvin.ai`):

```bash
venv/bin/python -c "from tools.api_client import save_environment; save_environment('<name>', 'https://<url>')"
```

## First-Time Login (No Keyring Credentials)

If `kelvin auth login` fails because there are no stored credentials, run the auth dialog. This pops up native macOS windows for the user to enter their credentials (password is masked):

```bash
venv/bin/python scripts/auth-dialog.py https://<resolved-url>
```

Tell the user a login window will pop up. After it completes, verify the token as in step 3.

## SDK Version Check

After login, check the output for a version mismatch warning like:
```
Current: 9.7.3 Recommended: 9.4.4
```

If mismatched, install the recommended version:
```bash
venv/bin/pip install kelvin-sdk==<recommended-version>
```

This is important — older platforms don't support newer SDK features, and some API endpoints may not exist.

## Fetch API Spec

After successful login, fetch the platform's OpenAPI spec so you can verify endpoints before calling them:

```bash
venv/bin/python tools/api_spec.py --env <env-name> fetch
```

This caches the spec locally. Only needs to be done once per environment (or after a platform upgrade).

## Rules

- ALWAYS use `venv/bin/kelvin` — never a system or global kelvin binary.
- Environment URLs vary: some use `.kelvininc.com`, others `.kelvin.ai`. Always resolve from config.json.
- If the environment name is not found in config.json, ask the user for the URL.
- NEVER ask the user to paste their password into the chat — always use `scripts/auth-dialog.py` for credential entry.
- After login, always check for SDK version mismatch and fix if needed.
- After login, always fetch the API spec for endpoint verification.

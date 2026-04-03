# Grocery Checklist Setup

No external service is required for the pantry state itself.

Requirements:
- `python3`
- `openclaw`
- Telegram already configured in OpenClaw if you want inline checklist buttons

Smoke test:

```bash
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh need "salt" "eggs"
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh show
```

Telegram dry run:

```bash
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh render-telegram --target "1351660348" --dry-run
```

If you want a custom state location:

```bash
export GROCERY_STATE_FILE=/path/to/state.json
```

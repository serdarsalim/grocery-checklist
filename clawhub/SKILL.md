---
name: grocery-checklist
description: "Persistent pantry-backed grocery checklist for OpenClaw, intended for normal conversational use with Telegram shopping-list UI."
version: 1.0.0
user-invocable: true
metadata:
  openclaw:
    emoji: "🛒"
    requires:
      bins:
        - bash
        - python3
        - openclaw
    reads:
      - ~/.openclaw/openclaw.json
    writes:
      - ~/.openclaw/data/grocery-checklist/state.json
      - ~/.openclaw/data/grocery-checklist/telegram-bot-state.json
---

# Grocery Checklist

This skill stores grocery state locally and supports a Telegram checklist UX.

Intended usage:
- OpenClaw handles conversation normally
- this skill provides grocery state and actions
- Telegram renders shopping and pantry views
- the managed OpenClaw route is the primary install mode

Runtime behavior:
- reads Telegram account config from `~/.openclaw/openclaw.json`
- writes pantry state to `~/.openclaw/data/grocery-checklist/state.json`
- writes Telegram polling state to `~/.openclaw/data/grocery-checklist/telegram-bot-state.json`
- uses the bundled wrapper at `scripts/grocery.sh`

Use it for:
- `I ran out of salt`
- `Add milk and eggs to groceries`
- `What do I need to buy?`
- `Mark eggs bought`

Wrapper:

```bash
bash <skill_dir>/scripts/grocery.sh ...
```

Core states:
- `needed`
- `have`

Telegram callbacks use:

```text
callback_data: gchk:...
```

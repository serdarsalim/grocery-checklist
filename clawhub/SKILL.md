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
- `I'm shopping now`
- `Should I go shopping today?`

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

Behavior guidance:
- treat natural grocery mutation phrasing as state changes
- treat `show me the shopping list`, `what do I need to buy`, and “I am shopping now” phrasing as shopping-list renders
- treat `show me the pantry` and `what do I have` as pantry renders
- keep normal grocery conversation conversational
- after a Telegram UI render or callback, do not send a second explanatory message
- for successful Telegram UI actions, the ideal model output is exactly `NO_REPLY`

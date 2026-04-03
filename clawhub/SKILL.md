---
name: grocery-checklist
description: "Persistent pantry-backed grocery checklist for OpenClaw, with Telegram inline buttons for marking items bought."
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
---

# Grocery Checklist

This skill stores grocery state locally and supports a Telegram checklist UX.

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

---
name: grocery-checklist
description: "Persistent pantry-backed grocery checklist for OpenClaw, with Telegram inline buttons for marking items bought. Use when the user says they ran out of something, bought something, wants to see what groceries are needed, or taps grocery checklist buttons in Telegram."
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

Use this skill when the user wants a real grocery workflow, not a generic todo list.

This skill is the source of truth for:
- what is needed
- what is already in stock
- the Telegram shopping checklist

## Execution rule

Run the local wrapper directly:

```bash
bash <skill_dir>/scripts/grocery.sh ...
```

Do not use ACP, sessions, or memory files for grocery state.

## State model

Items only have two meaningful states:
- `needed`
- `have`

Interpret user intent as state changes:
- `I ran out of salt` -> `needed`
- `add eggs and milk` -> `needed`
- `I bought eggs` -> `have`
- `mark milk bought` -> `have`

This is not a task list. Do not create duplicate items for the same ingredient.

## Telegram behavior

When the conversation contains Telegram metadata with a `sender_id`, treat that as the Telegram target for checklist rendering.

Telegram button clicks arrive as plain text like:

```text
callback_data: gchk:have:abc123def4
```

If the callback starts with `gchk:`, call:

```bash
bash <skill_dir>/scripts/grocery.sh handle-callback "<raw callback text>" --target "<sender_id>"
```

The script will update state and redraw the Telegram checklist.

## Core commands

Mark items needed:

```bash
bash <skill_dir>/scripts/grocery.sh need "salt" "eggs"
```

Mark items bought / in stock:

```bash
bash <skill_dir>/scripts/grocery.sh have "salt"
```

Remove items:

```bash
bash <skill_dir>/scripts/grocery.sh remove "salt"
```

Show current shopping list:

```bash
bash <skill_dir>/scripts/grocery.sh show
```

Render the Telegram checklist:

```bash
bash <skill_dir>/scripts/grocery.sh render-telegram --target "1351660348"
```

Render pantry view instead:

```bash
bash <skill_dir>/scripts/grocery.sh render-telegram --target "1351660348" --mode all
```

## Agent rules

- Prefer direct execution over discussion when intent is clear.
- If the user asks `what do I need to buy`, render the Telegram checklist when `sender_id` is present; otherwise show the plain text list.
- After changing grocery state in Telegram, refresh the checklist immediately.
- Keep confirmations brief.
- If the item naming is obviously the same ingredient with different casing or punctuation, treat it as the same item.
- If the user asks for a full pantry view, use `--mode all`.
- If `sender_id` is missing, do not guess a Telegram target. Fall back to text.

## Storage

Default state file:

```text
~/.openclaw/data/grocery-checklist/state.json
```

Override with:

```text
GROCERY_STATE_FILE
```

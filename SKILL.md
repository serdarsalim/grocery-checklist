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
- `I didn't buy X`, `I forgot X`, `put X back` -> `needed` (undo)

This is not a task list. Do not create duplicate items for the same ingredient.

## Telegram behavior

When the conversation contains Telegram metadata with a `sender_id`, treat that as the Telegram target for checklist rendering.

Stay conversational for normal grocery chat. Do not behave like a rigid command parser.

Intent guidance:
- `I ran out of salt`, `add eggs`, `put milk in the shopping list` -> mutate grocery state
- `what do I need to buy`, `show me the shopping list`, `shopping view` -> render shopping list
- `i'm shopping now`, `i'm going shopping now`, and similar “I am shopping now” phrasing -> render shopping list immediately
- `show me the pantry`, `what do I have` -> render pantry view
- `I bought eggs`, `got milk`, `picked up bread` -> mark items `have`
- `I didn't buy X`, `I forgot X`, `missed X`, `put X back on the list` -> revert to `needed`
- `fix olive oil`, merge requests, and rename requests -> canonicalize grocery items
- `should I go shopping today?` or similar -> inspect current grocery state and answer briefly based on what is still needed

Telegram button clicks arrive as plain text like:

```text
callback_data: gchk:have:abc123def4
```

If the callback starts with `gchk:`, call:

```bash
bash <skill_dir>/scripts/grocery.sh handle-callback "<raw callback text>" --target "<sender_id>" --account grocery
```

The script will update state and redraw the Telegram checklist.

For Telegram UI actions:
- `render-telegram`
- pantry render via `--mode all`
- `gchk:...` callbacks

do not add a second explanatory message after the UI updates. The ideal model output after a successful UI action is exactly `NO_REPLY`.

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

Render the Telegram checklist (--target is optional; omit to send to all active viewers):

```bash
bash <skill_dir>/scripts/grocery.sh render-telegram --account grocery
```

Show items that have been `needed` for more than 14 days:

```bash
bash <skill_dir>/scripts/grocery.sh stale
```

Override threshold:

```bash
bash <skill_dir>/scripts/grocery.sh stale --days 7
```

Render pantry view instead:

```bash
bash <skill_dir>/scripts/grocery.sh render-telegram --account grocery --mode all
```

## Agent rules

- Prefer direct execution over discussion when intent is clear.
- If the user asks `what do I need to buy`, render the Telegram checklist when `sender_id` is present; otherwise show the plain text list.
- If the user indicates they are actively shopping right now, render the Telegram checklist immediately when `sender_id` is present.
- After changing grocery state in Telegram, refresh the checklist immediately.
- Keep confirmations brief.
- If the item naming is obviously the same ingredient with different casing or punctuation, treat it as the same item.
- If the user asks for a full pantry view, use `--mode all`.
- Never fall back to describing the list in text. If render fails, say only "Couldn't render the view."
- Never summarize the checklist or pantry UI after a Telegram render or callback.

## Storage

Default state file:

```text
~/.openclaw/data/grocery-checklist/state.json
```

Override with:

```text
GROCERY_STATE_FILE
```

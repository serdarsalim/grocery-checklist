# Grocery Checklist Agent Notes

This skill is intentionally small and local-first.

## Source of truth

- Pantry and shopping state live in `~/.openclaw/data/grocery-checklist/state.json` by default.
- Telegram is only a UI surface.
- Do not mirror this state into Todoist unless the user explicitly asks.

## Operational rules

- Use `/Users/slm/.openclaw/skills/grocery-checklist/scripts/grocery.sh` directly.
- Prefer item-state mutations over chatty explanations.
- Treat `ran out`, `need`, `add to groceries`, `shopping list`, and `buy list` as grocery intents.
- Treat `bought`, `got`, `picked up`, and `mark done` as `have`.
- When a Telegram callback contains `gchk:`, run `handle-callback` and let the script redraw the checklist.
- Parse `sender_id` from the incoming Telegram metadata when present.
- If a Telegram target is unavailable, fall back to the text list instead of inventing a target.

## UX rules

- The default view is the shopping list, not the full pantry.
- Full pantry view is secondary and should be shown only when asked or when the user taps the pantry button.
- Keep item names short and canonical where possible.

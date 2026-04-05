# Grocery Checklist Agent Notes

This skill is intentionally small and local-first.

## Source of truth

- Pantry and shopping state live in `~/.openclaw/data/grocery-checklist/state.json` by default.
- Telegram is only a UI surface.
- Do not mirror this state into Todoist unless the user explicitly asks.

## Operational rules

- Use `/Users/slm/.openclaw/skills/grocery-checklist/scripts/grocery.sh` directly.
- Prefer the `mutate_grocery_items` tool for add/buy/remove/rename/merge intents and `render_grocery_view` for UI renders.
- Stay conversational for normal grocery chat. Do not behave like a rigid command bot.
- Prefer item-state mutations over chatty explanations.
- Never claim an item was added, bought, removed, renamed, or merged unless the corresponding wrapper command already succeeded in the current turn.
- Treat `ran out`, `need`, `add to groceries`, `put ... in the shopping list`, and similar phrasing as grocery mutation intents.
- Treat `show me the shopping list`, `shopping view`, `what do I need to buy`, `i'm shopping now`, `im shopping now`, `i'm going shopping now`, `im going shopping now`, and similar “I am shopping now” phrasing as shopping-list view intents. If the user indicates they are currently shopping, show the shopping list immediately instead of giving advice or small talk.
- Treat `show me the pantry`, `show pantry`, `pantry view`, `what do I have`, and `what's in the pantry` as full pantry view intents.
- Treat `bought`, `got`, `picked up`, and `mark done` as `have`.
- Treat corrections like `fix olive oil`, `olive and oil shouldn't be separate`, merge requests, and rename requests as grocery maintenance intents.
- If the user asks broad grocery questions like `should I go shopping today?` or `do I need to go shopping`, inspect the current grocery state and answer briefly based on what is still needed.
- When a Telegram callback contains `gchk:`, run `handle-callback` and let the script redraw the checklist.
- Parse `sender_id` from the incoming Telegram metadata when present.
- If a Telegram target is unavailable, fall back to the text list instead of inventing a target.

## UX rules

- The default view is the shopping list, not the full pantry.
- Full pantry view is secondary and should be shown only when asked or when the user taps the pantry button.
- Keep item names short and canonical where possible.
- After a Telegram UI action like `render-telegram`, pantry render, or a `gchk:...` callback, do not narrate the UI. The user-visible result should be the Telegram UI update only.
- For Telegram UI actions, the ideal terminal/model response is exactly `NO_REPLY`.
- For non-UI grocery mutations, confirmations should be brief.
- If a mutation command did not run yet, ask or execute; do not bluff success.

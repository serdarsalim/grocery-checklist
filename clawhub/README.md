# Grocery Checklist

Grocery Checklist is a pantry-backed shopping skill for OpenClaw.

It supports:
- persistent `needed` / `have` state
- natural language pantry updates like `I ran out of salt`
- shopping-list queries like `what do I need to buy`
- Telegram inline checklist buttons
- staged selection with `Done` to commit bought items

## What this skill is

This is not a generic todo list.

It is a lightweight pantry state machine:
- `ran out of eggs` -> eggs become `needed`
- `bought eggs` -> eggs become `have`
- `what do I need to buy` -> only `needed` items are shown

If you want OpenClaw to be the source of truth and Telegram to be the shopping UI, this is the right shape.

## What the user needs

- `python3`
- `openclaw`
- a working OpenClaw Telegram bot if you want the inline checklist UI

Optional:
- a dedicated grocery Telegram bot bound to a dedicated OpenClaw agent

## Install summary

1. Put the skill at `~/.openclaw/skills/grocery-checklist`
2. Verify `python3` and `openclaw` are installed
3. Run the wrapper in `scripts/grocery.sh`
4. Optionally bind a dedicated Telegram bot/account to grocery-only routing
5. Restart the OpenClaw gateway

For the full process, read [SETUP.md](./SETUP.md).

## Good test prompts

- `I ran out of salt`
- `I ran out of eggs, rice, and bread`
- `what do I need to buy`
- `I bought eggs`

## For agents

Agent-specific operating rules live in [AGENTS.md](./AGENTS.md).

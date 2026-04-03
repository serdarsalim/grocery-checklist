# Setup

This is the shortest reliable setup for a real user.

The goal is not just "show a list." The goal is to keep pantry state in OpenClaw and expose a Telegram-friendly shopping checklist.

## 1. Install the skill

Put this skill at:

```bash
~/.openclaw/skills/grocery-checklist
```

## 2. Verify prerequisites

You need:

```bash
python3 --version
openclaw --version
```

## 3. Smoke test the local wrapper

Run:

```bash
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh need salt eggs
bash ~/.openclaw/skills/grocery-checklist/scripts/grocery.sh show
```

## 4. Optional: dedicated Telegram bot

This skill works best when the grocery bot is separate from your main assistant bot.

Typical shape:

```bash
openclaw channels add --channel telegram --account grocery --name "Grocery Shopping" --token <telegram-bot-token>
openclaw agents add grocery --workspace ~/.openclaw/workspace --bind telegram:grocery --non-interactive
```

Then route grocery-only prompts to:

```bash
~/.openclaw/workspace/grocery.sh
```

## 5. Allow exec approvals

If your OpenClaw setup requires exec approvals, allowlist:

```bash
~/.openclaw/workspace/grocery.sh
~/.openclaw/skills/grocery-checklist/scripts/*.py
```

## 6. Restart OpenClaw gateway

```bash
openclaw gateway restart
```

## 7. Smoke test in chat

Try:

```text
I ran out of salt and eggs
what do I need to buy
I bought eggs
```

## 8. Smoke test in Telegram

If you wired a Telegram bot:
- ask `what do i need to buy`
- tap a few items
- tap `Done`

## Common failures

`exec approval is required`
- allowlist the grocery wrapper and script paths

`wrong Telegram bot receives the checklist`
- make sure the grocery wrapper passes `--account grocery`

`button taps do nothing`
- confirm callback routing preserves `gchk:...` payloads

`list shows prose instead of checklist`
- the agent prompt is narrating instead of executing the wrapper directly
